### Recommendation

*   **Engine:** claude
*   **Provider:** anthropic
*   **Model:** sonnet-4-6
*   **Effort:** Standard (S)

### Reasoning

The S2 work consists of implementing well-defined, hermetic Python components: a data schema, a merge/deduplication algorithm, a validator with a strict parity requirement (L-066-1), and system wiring. This class of task prioritizes rapid, high-fidelity code generation for well-specified logic over the frontier reasoning capabilities required in S1 for prompt-driven analysis. Claude Sonnet 4.6 offers the optimal trade-off, providing excellent performance for this type of engineering work with lower latency and cost compared to a flagship model. This maximizes developer velocity for a session where the primary risk is precise implementation of a known specification, not exploratory AI analysis.