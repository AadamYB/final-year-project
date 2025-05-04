// .ci.yaml templates

export const CODE_SNIPPETS = {
  default: `# 🛠️ Default CI Pipeline Configuration
lint: true
format: true
build: true
test: true

# Optional breakpoint controls
pause_before_clone: false
pause_after_clone: false
pause_before_build: false
pause_after_build: false
pause_before_test: false
pause_after_test: false

# Optional custom commands to run after build/test
run_commands:
  - echo "🎉 Default build and test completed!"`,

  python: `# 🐍 Python Project Example
lint: true
format: true
build: true
test: true

# Optional debugging pause breakpoints
pause_before_clone: true
pause_after_clone: false
pause_before_build: false
pause_after_build: true
pause_before_test: false
pause_after_test: false

run_commands:
  - echo "✅ Python pipeline completed!"
  - pytest tests/`,

  nodejs: `# 🧱 Node.js Project Example
lint: false
format: false
build: true
test: true

pause_before_clone: false
pause_after_clone: false
pause_before_build: false
pause_after_build: false
pause_before_test: false
pause_after_test: false

run_commands:
  - echo "📦 Building Node.js app..."
  - npm install
  - npm run build
  - npm test`
};