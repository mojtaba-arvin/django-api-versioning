.PHONY: release website-check

# Run the website's complete local verification pipeline.
website-check:
\t@pnpm --dir website install --frozen-lockfile
\t@pnpm --dir website run format:check
\t@pnpm --dir website run typecheck
\t@pnpm --dir website test
\t@pnpm --dir website run build
\t@pnpm --dir website run test:dist:root
\t@pnpm --dir website run test:dist:subpath


# Bootstrap the repository before loading the release implementation. This
# prevents Bash from continuing with an outdated maintain.sh after a self-update.
release:
	@bash scripts/release_bootstrap.sh
