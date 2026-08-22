/**
 * Admin Dispatch Simulation & Visualizer
 */
async function simulateDispatch(algorithm = "NEAREST") {
  console.log(`[Dispatch] Running automated assignment simulation with ${algorithm}...`);
  return await APIClient.post("/api/dispatch/trigger/", { algorithm: algorithm });
}
