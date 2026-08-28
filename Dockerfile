FROM python:3.12-slim

# Copy the uv binary itself from Astral's official image, rather than installing
# it via pip — this is the pattern uv's own docs recommend for Docker.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first, separately from the app code, so Docker can cache
# this (slow) layer and only re-run it when pyproject.toml/uv.lock actually change —
# not on every single code edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Now copy the actual application code and finish the install.
COPY . .
RUN uv sync --frozen

EXPOSE 8000

# Production server — fastapi's "run" command (not "dev", which is reload-enabled
# and meant for local development only). ${PORT:-8000} lets a hosting platform
# (Render) inject its own port via the PORT env var, while still defaulting to
# 8000 for local testing where PORT isn't set.
#
# JSON array form (not a plain shell string) so Docker doesn't wrap this in its
# own implicit shell wrapper — but we still need a shell for the ${PORT:-8000}
# substitution, so we invoke one explicitly and use `exec` to replace that shell
# process with the real command, rather than running it as the shell's child.
# That makes the app itself PID 1, so it receives Docker's shutdown signals
# directly instead of the shell swallowing them.
CMD ["sh", "-c", "exec uv run fastapi run app/main.py --host 0.0.0.0 --port ${PORT:-8000}"]
