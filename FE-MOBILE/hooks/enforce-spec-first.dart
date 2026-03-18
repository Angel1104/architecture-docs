#!/usr/bin/env dart
/// comocom Flutter spec-first enforcement hook.
///
/// Runs on PreToolUse for Write and Edit tools.
/// Blocks writes to lib/features/ implementation code if no corresponding
/// reviewed spec exists.
///
/// Hook protocol:
///   - Reads JSON from stdin: {"tool_name": "...", "tool_input": {"file_path": "...", ...}}
///   - Exit 0 silently to allow
///   - Print JSON with permissionDecision: "deny" to block

import 'dart:convert';
import 'dart:io';

/// Normalize path separators to forward slashes for consistent matching.
String normalizePath(String path) => path.replaceAll(r'\', '/');

/// Heuristic: extract possible feature names from a lib/features/ file path.
///
/// Examples:
///   lib/features/user_profile/domain/entities/user_profile.dart → {"user-profile"}
///   lib/features/hire-an-agent/application/blocs/hire_agent_bloc.dart → {"hire-agent", "hire"}
Set<String> inferFeatureNames(String filePath) {
  final normalized = normalizePath(filePath);

  // Extract the feature segment from lib/features/<feature>/...
  final featuresMatch =
      RegExp(r'lib/features/([^/]+)/').firstMatch(normalized);
  if (featuresMatch != null) {
    final featureSegment = featuresMatch.group(1)!;
    // Normalize underscores → hyphens
    final kebab = featureSegment.replaceAll('_', '-');
    final names = <String>{kebab};
    final parts = kebab.split('-');
    if (parts.length > 1) {
      names.add(parts[0]);
      names.add(parts.sublist(0, 2).join('-'));
    }
    return names;
  }

  // Fallback: use the file basename
  final basename =
      filePath.split(RegExp(r'[/\\]')).last.replaceAll(RegExp(r'\.\w+$'), '');
  final kebab = basename.replaceAll('_', '-');
  final names = <String>{kebab};
  final parts = kebab.split('-');
  if (parts.length > 1) {
    names.add(parts[0]);
    names.add(parts.sublist(0, 2).join('-'));
  }
  return names;
}

/// Check if any spec file in [specsDir] matches the inferred feature names.
/// Returns (matchingSpecFile, allSpecFiles).
(String?, List<String>) findMatchingSpec(
    Directory specsDir, Set<String> featureNames) {
  List<String> specFiles;
  try {
    specFiles = specsDir
        .listSync()
        .whereType<File>()
        .map((f) => f.uri.pathSegments.last)
        .where((name) => name.endsWith('.spec.md'))
        .toList();
  } catch (_) {
    return (null, []);
  }

  for (final specFile in specFiles) {
    final specName = specFile.replaceAll('.spec.md', '');
    for (final featureName in featureNames) {
      if (specName.contains(featureName) || featureName.contains(specName)) {
        return (specFile, specFiles);
      }
    }
  }
  return (null, specFiles);
}

/// Check if a spec file has REVIEWED or APPROVED status.
bool isSpecReviewed(File specFile) {
  try {
    // Read only first 2000 characters for performance
    final raf = specFile.openSync();
    final bytes = raf.readSync(2000);
    raf.closeSync();
    final content = utf8.decode(bytes, allowMalformed: true);
    return RegExp(r'Status\s*\|\s*(REVIEWED|APPROVED)', caseSensitive: false)
        .hasMatch(content);
  } catch (_) {
    return false;
  }
}

/// Print a deny decision and exit 0.
void deny(String reason) {
  final output = {
    'hookSpecificOutput': {
      'hookEventName': 'PreToolUse',
      'permissionDecision': 'deny',
      'permissionDecisionReason': reason,
    }
  };
  stdout.write(jsonEncode(output));
  exit(0);
}

/// Print an allow decision with a warning reason and exit 0.
void warn(String reason) {
  final output = {
    'hookSpecificOutput': {
      'hookEventName': 'PreToolUse',
      'permissionDecision': 'allow',
      'permissionDecisionReason': reason,
    }
  };
  stdout.write(jsonEncode(output));
  exit(0);
}

void main() {
  // Read JSON from stdin
  Map<String, dynamic> inputData;
  try {
    final raw = stdin.readLineSync(encoding: utf8) ?? '';
    if (raw.isEmpty) exit(0);
    inputData = jsonDecode(raw) as Map<String, dynamic>;
  } catch (_) {
    exit(0);
  }

  final toolName = inputData['tool_name'] as String? ?? '';
  final toolInput = inputData['tool_input'] as Map<String, dynamic>? ?? {};

  // Only enforce for Write and Edit tools
  if (toolName != 'Write' && toolName != 'Edit') exit(0);

  final filePath =
      (toolInput['file_path'] as String? ?? toolInput['path'] as String? ?? '')
          .trim();
  if (filePath.isEmpty) exit(0);

  final normalizedPath = normalizePath(filePath);

  // Only enforce for lib/features/ paths
  final isFlutterFeatureFile =
      RegExp(r'(^|/)lib/features/').hasMatch(normalizedPath);
  if (!isFlutterFeatureFile) exit(0);

  // Skip Dart generated files — build_runner outputs should not be blocked
  final basename = filePath.split(RegExp(r'[/\\]')).last;
  if (basename.endsWith('.g.dart') || basename.endsWith('.freezed.dart')) {
    exit(0);
  }

  // Locate project directory from environment variable
  final projectDir =
      Platform.environment['CLAUDE_PROJECT_DIR'] ?? Directory.current.path;
  final specsDir = Directory('$projectDir/specs');

  // No specs/ directory at all
  if (!specsDir.existsSync()) {
    deny(
      'SPEC-FIRST VIOLATION: No specs/ directory found.\n\n'
      'The comocom Flutter methodology requires a specification before implementation.\n'
      'Run `/spec-init <feature-name>` to create a spec first.\n\n'
      'Blocked write to: $filePath',
    );
  }

  // Infer feature names and look for a matching spec
  final featureNames = inferFeatureNames(filePath);
  final (matchingSpec, allSpecs) = findMatchingSpec(specsDir, featureNames);

  if (allSpecs.isEmpty) {
    deny(
      'SPEC-FIRST VIOLATION: No spec files found in specs/.\n\n'
      'The comocom Flutter methodology requires a reviewed specification before '
      'writing implementation code.\n'
      'Run `/spec-init <feature-name>` to create a spec, then '
      '`/spec-review <feature-name>` to review it.\n\n'
      'Blocked write to: $filePath',
    );
  }

  if (matchingSpec != null) {
    // Found a matching spec — check if it's reviewed
    final specFile = File('${specsDir.path}/$matchingSpec');
    if (isSpecReviewed(specFile)) {
      exit(0); // All good — reviewed spec exists
    } else {
      warn(
        'SPEC-FIRST WARNING: Found spec \'$matchingSpec\' but it is not yet REVIEWED.\n'
        'Run `/spec-review ${matchingSpec.replaceAll('.spec.md', '')}` before implementing.\n'
        'Proceeding with write to: $filePath',
      );
    }
  } else {
    // No matching spec — check if ANY reviewed spec exists (soft enforcement)
    final hasAnyReviewed = allSpecs.any(
      (sf) => isSpecReviewed(File('${specsDir.path}/$sf')),
    );
    if (hasAnyReviewed) {
      warn(
        'SPEC-FIRST WARNING: No spec matches this file.\n'
        'Inferred feature names: ${featureNames.toList()..sort()}\n'
        'Existing specs: ${allSpecs..sort()}\n'
        'Consider creating a spec for this feature with `/spec-init <feature-name>`.\n'
        'Proceeding with write to: $filePath',
      );
    } else {
      deny(
        'SPEC-FIRST VIOLATION: No reviewed specs found.\n\n'
        'Specs exist but none have REVIEWED/APPROVED status.\n'
        'Run `/spec-review <feature-name>` to review a spec before implementing.\n\n'
        'Blocked write to: $filePath',
      );
    }
  }
}
