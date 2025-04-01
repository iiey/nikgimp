# Coding Guidelines
- Use double quotes `"my_str"` for strings and nake case for [variable naming](https://google.github.io/styleguide/pyguide.html#316-naming)
- Use [black](https://github.com/psf/black) for consistency code format
- Use [pylint](https://pypi.org/project/pylint) to check code quality
- Always use type hints for function parameter(s) and return value(s) if applicable
- Follow best practices for [commit message convention](https://cbea.ms/git-commit/#seven-rules)

# Versioning
- Our version scheme: `major.minor.patch[-rc]` where:
  - `major`: **always** `3` indicating GIMP `v3.x` compatibility
  - `minor`: incremented for breaking changes, new features
  - `patch`: incremented for bug fixes, minor changes
  - `-rc`: after an official release, the next version will has *release candidate* suffix to different with the previous version
- For details see [semantic versioning](https://semver.org/)
