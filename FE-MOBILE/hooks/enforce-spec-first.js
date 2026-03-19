#!/usr/bin/env node
/**
 * Flutter spec-first enforcement hook.
 *
 * Runs on PreToolUse for Write and Edit tools.
 * Blocks writes to lib/features/ implementation code if no corresponding
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
 *   - Matching spec + APPROVED → ALLOW
 *   - Matching spec + not APPROVED → WARN (allow, but flag)
 *   - No matching spec found   → DENY (feature has no spec — must create one)
 *
 * NOTE: Rewritten from Dart to Node.js — Dart requires the full SDK in PATH
 * to execute as a shell hook. Node.js is always available in the Claude Code env.
 */

const fs = require('fs')
const path = require('path')
const readline = require('readline')

/** Normalize path separators to forward slashes */
function normalizePath(p) {
  return p.replace(/\\/g, '/')
}

/**
 * Heuristic: extract possible feature names from a lib/features/ file path.
 *
 * Flutter uses snake_case for directories, so we normalize to kebab-case.
 *
 * Examples:
 *   lib/features/user_profile/domain/entities/user_profile.dart → ["user-profile", "user"]
 *   lib/features/auth/presentation/screens/login_screen.dart → ["auth"]
 */
function inferFeatureNames(filePath) {
  const normalized = normalizePath(filePath)
  const names = new Set()

  const match = normalized.match(/lib\/features\/([^/]+)\//)
  if (match) {
    const featureSegment = match[1]
    // Normalize snake_case → kebab-case (Flutter convention)
    const kebab = featureSegment.replace(/_/g, '-')
    names.add(kebab)
    const parts = kebab.split('-')
    if (parts.length > 1) {
      names.add(parts[0])
      names.add(parts.slice(0, 2).join('-'))
    }
    return names
  }

  // Fallback: use the file basename (strip .dart extension)
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
 * Find a matching spec file in specsDir for the given feature names.
 * Returns [matchingSpecFile | null, allSpecFiles]
 */
function findMatchingSpec(specsDir, featureNames) {
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
    for (const featureName of featureNames) {
      if (specName.includes(featureName) || featureName.includes(specName)) {
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

  // Only enforce for lib/features/ paths
  if (!/(?:^|\/)lib\/features\//.test(normalizedPath)) process.exit(0)

  // Skip build_runner generated files — never block codegen outputs
  const basename = path.basename(filePath)
  if (basename.endsWith('.g.dart') || basename.endsWith('.freezed.dart')) process.exit(0)

  // Locate project directory
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd()
  const specsDir = path.join(projectDir, 'specs', 'cr')

  // No specs/cr/ directory at all
  if (!fs.existsSync(specsDir)) {
    deny(
      'SPEC-FIRST VIOLATION: No specs/cr/ directory found.\n\n' +
      'The Flutter SDM kit requires a specification before implementation.\n' +
      'Run `/intake <description>` to create a CR item, then `/spec <cr-id>` to create a spec.\n\n' +
      `Blocked write to: ${filePath}`
    )
  }

  // Infer feature names and look for a matching spec
  const featureNames = inferFeatureNames(filePath)
  const [matchingSpec, allSpecs] = findMatchingSpec(specsDir, featureNames)

  if (allSpecs.length === 0) {
    deny(
      'SPEC-FIRST VIOLATION: No spec files found in specs/cr/.\n\n' +
      'The Flutter SDM kit requires a reviewed specification before writing implementation code.\n' +
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
    // P0 FIX: No matching spec for this specific feature → DENY always.
    // A reviewed spec for a different feature does not cover this one.
    deny(
      'SPEC-FIRST VIOLATION: No spec found for this feature.\n\n' +
      `Inferred feature names: ${[...featureNames].sort().join(', ')}\n` +
      `Existing specs: ${allSpecs.sort().join(', ') || '(none)'}\n\n` +
      'Every feature requires its own reviewed spec before implementation.\n' +
      'Run `/intake <description>` to create a CR item, then `/spec <cr-id>`.\n\n' +
      `Blocked write to: ${filePath}`
    )
  }
}

main()
