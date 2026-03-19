#!/usr/bin/env node
/**
 * NestJS spec-first enforcement hook.
 *
 * Runs on PreToolUse for Write and Edit tools.
 * Blocks writes to src/modules/ implementation code if no corresponding
 * reviewed spec exists in specs/cr/.
 *
 * Hook protocol:
 *   - Reads JSON from stdin: {"tool_name": "...", "tool_input": {"file_path": "...", ...}}
 *   - Exit 0 silently to allow
 *   - Print JSON with permissionDecision: "deny" to block
 *
 * Enforcement logic:
 *   - No specs/cr/ dir         → DENY
 *   - No spec files at all     → DENY
 *   - Matching spec found + APPROVED → ALLOW
 *   - Matching spec found + not APPROVED → WARN (allow, but flag)
 *   - No matching spec found   → DENY (module has no spec — must create one)
 */

const fs = require('fs')
const path = require('path')
const readline = require('readline')

/** Normalize path separators to forward slashes */
function normalizePath(p) {
  return p.replace(/\\/g, '/')
}

/**
 * Heuristic: extract possible module names from a src/ file path.
 *
 * Examples:
 *   src/modules/user-profile/domain/entities/User.ts → ["user-profile", "user"]
 *   src/modules/auth/application/use-cases/Login.ts → ["auth"]
 *   src/shared/infrastructure/prisma/PrismaService.ts → ["prisma", "shared"]
 */
function inferModuleNames(filePath) {
  const normalized = normalizePath(filePath)
  const names = new Set()

  const moduleMatch = normalized.match(/src\/modules\/([^/]+)\//)
  if (moduleMatch) {
    const moduleSegment = moduleMatch[1]
    const kebab = moduleSegment.replace(/_/g, '-')
    names.add(kebab)
    const parts = kebab.split('-')
    if (parts.length > 1) {
      names.add(parts[0])
      names.add(parts.slice(0, 2).join('-'))
    }
    return names
  }

  const sharedMatch = normalized.match(/src\/shared\/([^/]+)\//)
  if (sharedMatch) {
    names.add('shared')
    names.add(sharedMatch[1].replace(/_/g, '-'))
    return names
  }

  // Fallback: use the file basename
  const basename = path.basename(filePath, path.extname(filePath))
  const kebab = basename.replace(/_/g, '-')
  names.add(kebab)
  const parts = kebab.split('-')
  if (parts.length > 1) {
    names.add(parts[0])
    names.add(parts.slice(0, 2).join('-'))
  }
  return names
}

/**
 * Find a matching spec file in specsDir for the given module names.
 * Returns [matchingSpecFile | null, allSpecFiles]
 */
function findMatchingSpec(specsDir, moduleNames) {
  let specFiles = []
  try {
    specFiles = fs
      .readdirSync(specsDir)
      .filter(f => f.endsWith('.spec.md'))
  } catch {
    return [null, []]
  }

  for (const specFile of specFiles) {
    const specName = specFile.replace('.spec.md', '')
    for (const moduleName of moduleNames) {
      if (specName.includes(moduleName) || moduleName.includes(specName)) {
        return [specFile, specFiles]
      }
    }
  }
  return [null, specFiles]
}

/**
 * Check if a spec file has REVIEWED or APPROVED status.
 * Reads only the first 2000 characters for performance.
 */
function isSpecReviewed(specFilePath) {
  try {
    const fd = fs.openSync(specFilePath, 'r')
    const buf = Buffer.alloc(2000)
    fs.readSync(fd, buf, 0, 2000, 0)
    fs.closeSync(fd)
    const content = buf.toString('utf8')
    return /Status\s*\|\s*(REVIEWED|APPROVED)/i.test(content)
  } catch {
    return false
  }
}

function deny(reason) {
  const output = {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }
  process.stdout.write(JSON.stringify(output))
  process.exit(0)
}

function warn(reason) {
  const output = {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'allow',
      permissionDecisionReason: reason,
    },
  }
  process.stdout.write(JSON.stringify(output))
  process.exit(0)
}

async function main() {
  // Read JSON from stdin
  let inputData
  try {
    const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity })
    const lines = []
    for await (const line of rl) {
      lines.push(line)
    }
    const raw = lines.join('\n').trim()
    if (!raw) process.exit(0)
    inputData = JSON.parse(raw)
  } catch {
    process.exit(0)
  }

  const toolName = inputData.tool_name || ''
  const toolInput = inputData.tool_input || {}

  // Only enforce for Write and Edit tools
  if (toolName !== 'Write' && toolName !== 'Edit') process.exit(0)

  const filePath = (toolInput.file_path || toolInput.path || '').trim()
  if (!filePath) process.exit(0)

  const normalizedPath = normalizePath(filePath)

  // Only enforce for src/ paths
  if (!/(?:^|\/)src\//.test(normalizedPath)) process.exit(0)

  // Skip generated files (.d.ts, test files, config files)
  const basename = path.basename(filePath)
  if (basename.endsWith('.d.ts')) process.exit(0)
  if (basename === 'tsconfig.json' || basename === 'jest.config.ts' || basename === '.env.example') process.exit(0)

  // Allow shared infrastructure (no spec needed for PrismaService, TraceInterceptor, etc.)
  if (/\/src\/shared\//.test(normalizedPath)) process.exit(0)

  // Allow main.ts and app.module.ts
  if (basename === 'main.ts' || basename === 'app.module.ts') process.exit(0)

  // Locate project directory
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd()
  const specsDir = path.join(projectDir, 'specs', 'cr')

  // No specs/cr/ directory at all
  if (!fs.existsSync(specsDir)) {
    deny(
      'SPEC-FIRST VIOLATION: No specs/cr/ directory found.\n\n' +
      'The NestJS SDM kit requires a specification before implementation.\n' +
      'Run `/intake <description>` to create a CR item, then `/spec <cr-id>` to create a spec.\n\n' +
      `Blocked write to: ${filePath}`
    )
  }

  // Infer module names and look for a matching spec
  const moduleNames = inferModuleNames(filePath)
  const [matchingSpec, allSpecs] = findMatchingSpec(specsDir, moduleNames)

  if (allSpecs.length === 0) {
    deny(
      'SPEC-FIRST VIOLATION: No spec files found in specs/cr/.\n\n' +
      'The NestJS SDM kit requires a reviewed specification before writing implementation code.\n' +
      'Run `/intake <description>` then `/spec <cr-id>` to create and review a spec.\n\n' +
      `Blocked write to: ${filePath}`
    )
  }

  if (matchingSpec !== null) {
    const specFilePath = path.join(specsDir, matchingSpec)
    if (isSpecReviewed(specFilePath)) {
      process.exit(0) // All good — reviewed spec exists
    } else {
      warn(
        `SPEC-FIRST WARNING: Found spec '${matchingSpec}' but it is not yet APPROVED.\n` +
        `Run '/spec <cr-id>' and complete the review before implementing.\n` +
        `Proceeding with write to: ${filePath}`
      )
    }
  } else {
    // P0 FIX: No matching spec for this specific module → DENY always.
    // A reviewed spec for a different module does not cover this one.
    deny(
      'SPEC-FIRST VIOLATION: No spec found for this module.\n\n' +
      `Inferred module names: ${[...moduleNames].sort().join(', ')}\n` +
      `Existing specs: ${allSpecs.sort().join(', ') || '(none)'}\n\n` +
      'Every module requires its own reviewed spec before implementation.\n' +
      'Run `/intake <description>` to create a CR item, then `/spec <cr-id>`.\n\n' +
      `Blocked write to: ${filePath}`
    )
  }
}

main()
