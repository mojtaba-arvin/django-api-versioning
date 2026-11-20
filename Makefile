.PHONY: release

# Bootstrap the repository before loading the release implementation. This
# prevents Bash from continuing with an outdated maintain.sh after a self-update.
release:
	@bash scripts/release_bootstrap.sh
