# LlamaIndex Governed Retrieval Pattern Output

The retrieval function searches local policy context and then validates the data-bearing SQL through Metatate before returning an answer.

Expected behavior:

- the aggregate ARR query is allowed
- the answer excludes customer identifiers
- the retrieved source list is returned with the Metatate action message

If LlamaIndex is installed, the same function can be wrapped as a `FunctionTool`. Without LlamaIndex, the notebook runs the callable directly.
