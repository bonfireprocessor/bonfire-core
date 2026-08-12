# MyHDL Skill Convention Update Plan

## Scope

Align the MyHDL/VHDL skill and bonfire-core agent policy with the requested planning, tooling-failure, and local plan-directory conventions.

## Planned changes

1. Require a mandatory pre-implementation planning phase in the skill.
2. Require plans to describe bundle classes, synchronous logic, combinational logic, the testbench, and directed test cases as applicable.
3. Store English project plans in `.agents/pi/plan/`.
4. Add `.agents/pi/plan/` to the project `.gitignore` so implementation plans remain local.
5. Prohibit autonomous tooling repairs when required tools or dependencies are unavailable or unusable; stop and ask the user how to proceed.
6. Update the bonfire-core project profile and repository agent policy so the plan location is consistent.
7. Keep all project-local tracked changes on a dedicated feature branch.
8. Re-read the changed documentation and verify all referenced paths and policies are consistent.

## Verification

- Confirm the current branch is `feature/myhdl-skill-conventions`.
- Confirm `SKILL.md` contains the planning and tooling-failure requirements.
- Confirm `references/bonfire-core.md` applies those requirements to bonfire-core.
- Confirm `.agents.md` names `.agents/pi/plan/` as the plan directory.
- Confirm Git ignores `.agents/pi/plan/myhdl_skill_conventions.md`.
- Confirm the obsolete `.pi/plans/myhdl_skill_conventions.md` no longer exists.
- No RTL simulation, conversion, GHDL analysis, or synthesis is required because no hardware implementation changes are made.
