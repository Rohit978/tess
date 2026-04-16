from .agent_loop import AgenticLoop
from .brain import Brain


class ScriptedBrain:
    """Deterministic brain used for offline eval/regression cases."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.history = []

    def update_history(self, role, content):
        self.history.append({"role": role, "content": content})

    def generate_command(self, _):
        if self.responses:
            return self.responses.pop(0)
        return {"action": "final_reply", "content": "done"}


class PermissiveSecurity:
    def validate_action(self, action_dict):
        return True, "Action Permitted"


class BlockingSecurity:
    def validate_action(self, action_dict):
        if action_dict.get("action") == "execute_command":
            command = (action_dict.get("command") or "").lower()
            if "rm -rf" in command or "format" in command:
                return False, "Blocked Dangerous Command Pattern"
        return True, "Action Permitted"


def _evaluate_agentic_loop_cases():
    import tess_cli.core.agent_loop as loop_module

    results = []

    scenarios = [
        {
            "name": "invalid_then_recover",
            "brain": ScriptedBrain([
                {"content": "missing action"},
                {"action": "execute_command", "command": "echo ok"},
                {"action": "final_reply", "content": "done"},
            ]),
            "security": PermissiveSecurity(),
            "expect": lambda executed, loop: "execute_command" in executed and "final_reply" in executed and len(loop.last_reflections) >= 1,
        },
        {
            "name": "blocked_then_safe_alternative",
            "brain": ScriptedBrain([
                {"action": "execute_command", "command": "rm -rf C:\\"},
                {"action": "reply_op", "content": "I will use a safer approach."},
            ]),
            "security": BlockingSecurity(),
            "expect": lambda executed, loop: "reply_op" in executed and len(loop.last_reflections) >= 1,
        },
        {
            "name": "execution_failure_then_replan",
            "brain": ScriptedBrain([
                {"action": "execute_command", "command": "simulate-fail"},
                {"action": "web_search_op", "query": "alternative command"},
                {"action": "final_reply", "content": "Recovered"},
            ]),
            "security": PermissiveSecurity(),
            "expect": lambda executed, loop: "web_search_op" in executed and "final_reply" in executed and len(loop.last_reflections) >= 1,
        },
    ]

    original_process_action = loop_module.process_action
    original_print_thinking = loop_module.print_thinking
    original_clear_thinking = loop_module.clear_thinking
    original_print_tess_action = loop_module.print_tess_action
    original_print_error = loop_module.print_error

    try:
        for scenario in scenarios:
            executed = []

            def fake_process_action(action_data, *_args, **_kwargs):
                action = action_data.get("action")
                executed.append(action)
                if action == "execute_command" and "simulate-fail" in (action_data.get("command") or ""):
                    return "Error: command failed."
                return "OK"

            # Silence UI noise for deterministic eval output.
            loop_module.process_action = fake_process_action
            loop_module.print_thinking = lambda *_args, **_kwargs: None
            loop_module.clear_thinking = lambda *_args, **_kwargs: None
            loop_module.print_tess_action = lambda *_args, **_kwargs: None
            loop_module.print_error = lambda *_args, **_kwargs: None

            loop = AgenticLoop(
                brain=scenario["brain"],
                components={"security": scenario["security"]},
                max_steps=6,
                max_replans=3,
            )
            loop.run("Complete a task")
            passed = bool(scenario["expect"](executed, loop))
            results.append(
                {
                    "name": scenario["name"],
                    "passed": passed,
                    "executed_actions": executed,
                    "reflection_count": len(loop.last_reflections),
                }
            )
    finally:
        loop_module.process_action = original_process_action
        loop_module.print_thinking = original_print_thinking
        loop_module.clear_thinking = original_clear_thinking
        loop_module.print_tess_action = original_print_tess_action
        loop_module.print_error = original_print_error

    return results


def _evaluate_json_parsing_cases():
    brain = Brain()
    cases = [
        ("plain_json", '{"action":"reply_op","content":"ok"}', "reply_op"),
        ("markdown_json", '```json\n{"action":"youtube_op","query":"lofi"}\n```', "youtube_op"),
        ("trailing_text", '{"action":"broadcast_op","sub_action":"start"} extra', "broadcast_op"),
        ("invalid_json_fallback", "not valid json", "reply_op"),
    ]
    results = []
    for name, raw, expected_action in cases:
        parsed = brain._parse_json(raw)
        passed = parsed.get("action") == expected_action
        results.append(
            {
                "name": name,
                "passed": passed,
                "action": parsed.get("action"),
                "expected": expected_action,
            }
        )
    return results


def run_regression_suite():
    parse_results = _evaluate_json_parsing_cases()
    loop_results = _evaluate_agentic_loop_cases()
    all_results = parse_results + loop_results
    passed = sum(1 for r in all_results if r["passed"])
    total = len(all_results)
    pass_rate = (passed / total) * 100 if total else 0
    return {
        "passed": passed,
        "total": total,
        "pass_rate": round(pass_rate, 2),
        "threshold": 85.0,
        "ok": pass_rate >= 85.0,
        "results": all_results,
    }


def print_regression_summary(summary):
    status = "PASS" if summary["ok"] else "FAIL"
    print(f"[EVAL] {status} | Score: {summary['pass_rate']}% ({summary['passed']}/{summary['total']}) | Threshold: {summary['threshold']}%")
    for item in summary["results"]:
        marker = "✅" if item["passed"] else "❌"
        print(f"  {marker} {item['name']}")
