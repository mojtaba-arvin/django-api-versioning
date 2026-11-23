.PHONY: release website-check

# Run the website's complete local verification pipeline.
website-check:
	@pnpm --dir website install --frozen-lockfile
	@pnpm --dir website run format:check
	@pnpm --dir website run typecheck
	@pnpm --dir website test
	@pnpm --dir website run build
	@pnpm --dir website run test:dist:root
	@pnpm --dir website run test:dist:subpath


# Bootstrap the repository before loading the release implementation. This
# prevents Bash from continuing with an outdated maintain.sh after a self-update.
release:
	@bash scripts/release_bootstrap.sh
