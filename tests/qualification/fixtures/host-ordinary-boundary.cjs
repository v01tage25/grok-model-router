function ordinaryTurn(request, agentId, modelId) {
  return transport.send({ agentId, modelId, messages: request.messages, stream: true });
}
function responseStream(response) { return response.on("data", onData); }
