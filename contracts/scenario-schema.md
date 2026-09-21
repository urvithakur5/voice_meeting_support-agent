# Scenario Schema

Each test scenario should contain the following information:

## Scenario ID

Unique identifier for the test.

Example:
MIC-001

## User Input

What the user says to the agent.

## Expected Intent

The problem the agent should identify.

## Expected Tool

The diagnostic tool the agent should use, if any.

## Expected Tool Result

The expected result from the tool.

## Expected Agent Behavior

What the agent should say or do.

## Expected Final State

The expected final UI/system state.

Possible states:

- diagnosing
- action_required
- verifying
- resolved
- escalated

## Failure Condition

What should happen if the expected behavior fails.
