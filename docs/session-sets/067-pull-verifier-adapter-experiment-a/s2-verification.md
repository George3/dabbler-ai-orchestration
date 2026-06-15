# Set 067 S2 -- Cross-provider verification (gpt-5.4)

> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude
> orchestrator. Round 1.

I reviewed the S2-added surfaces only: `OpenAIBinding`, `GeminiBinding`, the `generation_params` threading, executor-config resolvers, and the added tests/live check.

Bottom line: I do **not** see a concrete functional desync bug in the shipped OpenAI or Gemini bindings under the current `pull_route` transcript discipline. The two adversarial areas you called out mostly check out:

- **OpenAI chaining**: `OpenAIBinding._to_input_items()` only serializes new `user` entries and `tool` results, and explicitly skips `assistant` turns. Given how `pull_route()` appends transcript entries (`assistant` first, then either `tool` results or a user nudge), that offset logic does not appear to drop or double-send items across normal turns, including the text-only nudge path.
- **Gemini positional matching**: `GeminiBinding._from_response()` synthesizes ids from part position, and `GeminiBinding._to_contents()` emits `functionResponse` parts in the driver’s `results` order while ignoring ids on the wire. Since `pull_route()` preserves `response.tool_calls` order when building `results`, same-name multi-call turns are positionally stable.

Other checks that passed:

- **OpenAI tool round-trip** is correct: `_from_response()` takes `call_id` from each `function_call`, and `_to_input_items()` sends it back as `function_call_output.call_id`.
- **Malformed OpenAI tool args** are handled safely: `_from_response()` catches JSON parse failures and falls back to `{}`.
- **OpenAI incomplete mapping** is correct: `_from_response()` maps `status=="incomplete"` plus `incomplete_details.reason=="max_output_tokens"` to `stop_reason="max_tokens"`.
- **Gemini token accounting** is honest: `_from_response()` adds `thoughtsTokenCount` into `output_tokens`.
- **Gemini thinking config branch** is implemented as intended: `model.startswith("gemini-3")` uses `thinkingLevel`; earlier models use bounded `thinkingBudget`.
- **Driver remained provider-agnostic**: `pull_route()` only gained `generation_params` plumbing and a load-config-once fix; the loop logic itself is unchanged.
- **Backward compatibility** looks intact: `caps_from_config({}) == PullCaps()`, explicit `caps=` still wins (`caps = caps or caps_from_config(config)`), and the FakeBinding remains compatible because its `request()` accepts `**kw`.
- **Cost accounting fields** line up with the live evidence: the `s2-headless-results.json` cost math exactly matches the token fields chosen for OpenAI and Gemini.

That said, I found one real robustness issue and two meaningful test-coverage gaps in exactly the risky areas.

### Findings

1. **OpenAI state mutation is not failure-atomic**
   - In `OpenAIBinding.request()`, the binding commits `self._sent_upto` **before** the HTTP call succeeds:
     ```python
     input_items, self._sent_upto = self._to_input_items(transcript, self._sent_upto)
     ```
   - If `client.post(...)`, `raise_for_status()`, or `resp.json()` fails, the binding has already advanced its local cursor without necessarily getting a new `response_id`.
   - Result: retrying the **same binding instance** can drop unsent user/tool items and desynchronize the stateful chain.
   - Current `pull_route()` usually aborts on exception and constructs a fresh binding per run, so this is not a demonstrated run-path failure today. But it is a real robustness hole in the stateful binding itself.

2. **The OpenAI nudge/desync edge is not directly pinned by tests**
   - The risky logic lives in `OpenAIBinding._to_input_items()` + `OpenAIBinding.request()`.
   - Existing OpenAI tests cover:
     - first-turn request body,
     - `previous_response_id` chaining after a tool call,
     - tool-output replay,
     - malformed arguments,
     - incomplete mapping.
   - They do **not** directly cover the specific adversarial case where the driver appends a **text-only user nudge** after a text-only assistant turn and the stateful offset must advance correctly across that extra user turn.
   - `TestLoopTermination.test_text_only_turn_nudges_then_verdict` exercises the driver with `FakeBinding`, not the OpenAI binding’s stateful serializer.

3. **The Gemini duplicate-same-name positional case is not directly pinned by tests**
   - The correctness-critical path is `GeminiBinding._from_response()` synthesizing ids from part order and `GeminiBinding._to_contents()` returning `functionResponse` parts in `results` order.
   - Current Gemini tests only cover a **single** `functionCall`, not the adversarial case of multiple same-name calls in one turn (e.g. two `read_file` calls).
   - There is also no direct test for the `gemini-3*` `thinkingLevel` branch; only the non-`gemini-3` `thinkingBudget` path is exercised.

So: implementation looks sound, but the most failure-prone S2 branches are not fully pinned, and the OpenAI binding has a small but real retry/desync robustness issue.

```json
{"verdict":"ISSUES_FOUND","issues":[{"severity":"Minor","claim":"OpenAI stateful chaining is safe across request failures","problem":"In `OpenAIBinding.request()`, `_sent_upto` is advanced before the HTTP call/JSON parse succeeds (`input_items, self._sent_upto = self._to_input_items(...)`). If the request fails and the same binding instance is retried, the binding can skip unsent transcript entries while `previous_response_id` is stale or absent, causing a multi-turn desync.","fix":"Stage the new offset in a local variable (e.g. `input_items, new_upto = ...`) and only assign `self._sent_upto = new_upto` after a successful response has been accepted and `self._response_id` has been updated."},{"severity":"Minor","claim":"The OpenAI tests pin the stateful offset/chaining edge cases","problem":"The suite does not directly test the exact text-only nudge path in the stateful OpenAI binding. `test_request_uses_responses_api_and_chains_previous_id` covers tool-result follow-up only, and `test_text_only_turn_nudges_then_verdict` uses `FakeBinding`, so the `_sent_upto` behavior across an assistant text-only turn plus user nudge is unpinned.","fix":"Add an OpenAI binding test that performs three sequential `request()` calls on one `OpenAIBinding` instance: initial user turn, a text-only assistant response leading to a user nudge, then a tool-call turn. Assert that turn 2 sends only the new nudge and turn 3 sends only the new `function_call_output`."},{"severity":"Minor","claim":"The Gemini tests pin positional matching for id-less multi-call turns","problem":"`GeminiBinding._from_response()` / `_to_contents()` rely on preserving order because Gemini has no wire ids, but the tests only cover a single `functionCall`. The adversarial case of two same-name calls in one turn (e.g. two `read_file` calls) is not directly verified, and the `gemini-3*` `thinkingLevel` branch is also untested.","fix":"Add a Gemini test with multiple same-name `functionCall` parts in one response, verify distinct synthesized ids, verify `pull_route()`/`_to_contents()` return `functionResponse` parts in the same order, and add a request-body test for a `gemini-3*` model asserting `thinkingConfig.thinkingLevel` is used instead of `thinkingBudget`."}]}
```
