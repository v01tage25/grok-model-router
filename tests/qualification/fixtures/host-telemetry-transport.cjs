function exportTelemetry(transport, serializedRequest) {
  return transport.send(serializedRequest);
}
const agentId = "agent-a";
const modelId = "model-a";
