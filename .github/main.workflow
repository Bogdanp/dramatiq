workflow "Lint and Test" {
  on = "push"
  resolves = ["Lint", "Test 3.5", "Test 3.6", "Test 3.7"]
}

action "Lint" {
  uses = "docker://python:3.7-slim"
  runs = ["/github/workspace/.github/actions/lint/lint.sh"]
}

action "Test 3.5" {
  uses = "./.github/actions/test35"
  runs = ["/github/workspace/.github/actions/test/test.sh"]
}

action "Test 3.6" {
  uses = "./.github/actions/test36"
  runs = ["/github/workspace/.github/actions/test/test.sh"]
}

action "Test 3.7" {
  uses = "./.github/actions/test37"
  runs = ["/github/workspace/.github/actions/test/test.sh"]
}
