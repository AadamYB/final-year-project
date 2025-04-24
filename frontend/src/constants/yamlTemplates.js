// frontend/src/constants/yamlTemplates.js

export const CODE_SNIPPETS = {
    default: `name: default_pipeline
  vessels:
    main:
      source:
        language: PYTHON
        file:
          name: script.py
          content: print("Hello from default")
        file_to_run: script.py
        type: CODE
      guardrails:
        retry_count: 1
        retry_wait: 10s
        runtime_cutoff: 1h
      notifications:
        emails:
          - user@example.com
        after_error: true
        after_on_demand: false`,
  
    python: `name: python_ci
  vessels:
    test_runner:
      source:
        language: PYTHON
        file:
          name: test_runner.py
          content: |
            import unittest
            unittest.main()
        file_to_run: test_runner.py
        type: CODE
      guardrails:
        retry_count: 0
        runtime_cutoff: 15m
      notifications:
        emails:
          - ci@example.com`,
  
    nodejs: `name: nodejs_deploy
  vessels:
    builder:
      source:
        language: NODEJS
        file:
          name: build.js
          content: console.log("Build complete")
        file_to_run: build.js
        type: CODE
      guardrails:
        retry_count: 2
        runtime_cutoff: 20m
      notifications:
        emails:
          - devops@example.com`
  };