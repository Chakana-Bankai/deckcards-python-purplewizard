import argparse
import os
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lib import (
        project_audit,
        project_sanitizer,
        duplicate_detector,
        manifest_manager,
        art_pipeline,
        audio_pipeline,
        qa_smoke,
        cli_validation,
        balance_simulator,
        ui_audit,
        engine_extractor,
        reports_build,
    )
else:
    from tools.lib import (
        project_audit,
        project_sanitizer,
        duplicate_detector,
        manifest_manager,
        art_pipeline,
        audio_pipeline,
        qa_smoke,
        cli_validation,
        balance_simulator,
        ui_audit,
        engine_extractor,
        reports_build,
    )

COMMANDS = {
    'project-audit': lambda dry_run: project_audit.run(dry_run=dry_run),
    'sanitize': lambda dry_run: project_sanitizer.run(dry_run=dry_run),
    'duplication-check': lambda dry_run: duplicate_detector.run(dry_run=dry_run),
    'manifest-audit': lambda dry_run: manifest_manager.run_audit(dry_run=dry_run),
    'art-audit': lambda dry_run: art_pipeline.run(dry_run=dry_run),
    'art-generate': None,
    'art-regenerate-missing': None,
    'art-validate': lambda dry_run: art_pipeline.validate(dry_run=dry_run),
    'art-promote': lambda dry_run: art_pipeline.promote(dry_run=dry_run),
    'audio-audit': lambda dry_run: audio_pipeline.run(dry_run=dry_run),
    'qa-smoke': lambda dry_run: qa_smoke.run(dry_run=dry_run),
    'cli-validate': lambda dry_run: cli_validation.run(dry_run=dry_run),
    'balance-sim': lambda dry_run: balance_simulator.run(dry_run=dry_run),
    'ui-audit': lambda dry_run: ui_audit.run(dry_run=dry_run),
    'engine-audit': lambda dry_run: engine_extractor.run(dry_run=dry_run),
    'reports-build': lambda dry_run: reports_build.run(dry_run=dry_run),
}


def main():
    parser = argparse.ArgumentParser(prog='chakana_studio', description='Chakana Studio Master CLI')
    parser.add_argument('command', choices=sorted(COMMANDS.keys()))
    parser.add_argument('--dry-run', action='store_true', dest='dry_run')
    parser.add_argument('--all', action='store_true', dest='generate_all')
    parser.add_argument('--force', action='store_true', dest='force')
    args = parser.parse_args()
    os.system('cls' if os.name == 'nt' else 'clear')
    if args.command == 'art-generate':
        if args.generate_all:
            report = art_pipeline.generate_all(dry_run=args.dry_run)
        else:
            report = art_pipeline.regenerate_missing(dry_run=args.dry_run, force=args.force)
    elif args.command == 'art-regenerate-missing':
        report = art_pipeline.regenerate_missing(dry_run=args.dry_run, force=args.force)
    else:
        report = COMMANDS[args.command](args.dry_run)
    print(f'[chakana_studio] report={report}')


if __name__ == '__main__':
    main()
