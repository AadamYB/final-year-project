// .ci.yaml templates

export const CODE_SNIPPETS = {
  default: `# Default CI Pipeline Template
lint: true
format: true
build: true
test: true

run_commands:
  - echo "🎉 Default build and test completed!"`,

  python: `# Python Project CI Example
lint: true
format: true
build: true
test: true

run_commands:
  - echo "🐍 Python project pipeline finished!"
  - pytest tests/`,

  nodejs: `# Node.js Project CI Example
lint: false
format: false
build: true
test: true

run_commands:
  - echo "🧱 Node.js project built!"
  - npm run build
  - npm test`
};