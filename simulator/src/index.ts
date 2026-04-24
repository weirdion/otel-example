#!/usr/bin/env node
/**
 * OTel Demo Simulator
 *
 * Simulates frontend user actions against the demo API.
 * Generates telemetry to demonstrate end-to-end tracing.
 */

import { program } from "commander";
import { randomUUID } from "crypto";

import { ApiClient } from "./api.js";
import { scenarios } from "./scenarios/index.js";
import { initTelemetry, shutdownTelemetry, withSpan } from "./telemetry/index.js";
import { UserContext } from "./types/index.js";

interface Options {
  url: string;
  scenario: string;
  count: string;
  userId?: string;
  orgId?: string;
  verbose: boolean;
  telemetryEndpoint?: string;
}

program
  .name("otel-simulator")
  .description("Simulate user actions for OTel demo")
  .requiredOption(
    "-u, --url <url>",
    "API Gateway URL",
    process.env.API_URL || "http://localhost:3000"
  )
  .option(
    "-s, --scenario <name>",
    "Scenario to run: login, order, browse, all",
    "all"
  )
  .option("-c, --count <number>", "Number of times to run scenario", "1")
  .option("--user-id <id>", "User ID for context")
  .option("--org-id <id>", "Organization ID for context")
  .option("-v, --verbose", "Verbose output", false)
  .option(
    "--telemetry-endpoint <url>",
    "OTLP endpoint for telemetry export"
  )
  .parse();

const options = program.opts<Options>();

async function main(): Promise<void> {
  // Initialize telemetry
  initTelemetry({
    otlpEndpoint: options.telemetryEndpoint,
    enabled: !!options.telemetryEndpoint,
  });

  // Create user context
  const userContext: UserContext = {
    userId: options.userId || `user-${randomUUID().slice(0, 8)}`,
    orgId: options.orgId || `org-${randomUUID().slice(0, 8)}`,
    sessionId: `sess-${randomUUID().slice(0, 8)}`,
  };

  console.log("OTel Demo Simulator");
  console.log("===================");
  console.log(`API URL:    ${options.url}`);
  console.log(`Scenario:   ${options.scenario}`);
  console.log(`Count:      ${options.count}`);
  console.log(`User ID:    ${userContext.userId}`);
  console.log(`Org ID:     ${userContext.orgId}`);
  console.log(`Session ID: ${userContext.sessionId}`);
  console.log();

  // Get scenario function
  const scenarioFn = scenarios[options.scenario];
  if (!scenarioFn) {
    console.error(
      `Unknown scenario: ${options.scenario}. Available: ${Object.keys(scenarios).join(", ")}`
    );
    process.exit(1);
  }

  // Create API client
  const client = new ApiClient(options.url, userContext, options.verbose);

  // Run scenarios
  const count = parseInt(options.count, 10);
  console.log(`Running '${options.scenario}' scenario ${count} time(s)...\n`);

  for (let i = 0; i < count; i++) {
    if (count > 1) {
      console.log(`\n[Run ${i + 1}/${count}]`);
    }

    try {
      await withSpan(
        `simulation.run.${i + 1}`,
        async () => {
          await scenarioFn(client);
        },
        {
          "simulation.scenario": options.scenario,
          "simulation.run": i + 1,
          "user.id": userContext.userId,
          "org.id": userContext.orgId,
        }
      );
      console.log("\n✓ Scenario completed successfully");
    } catch (error) {
      console.error(
        "\n✗ Scenario failed:",
        error instanceof Error ? error.message : error
      );
      if (options.verbose && error instanceof Error) {
        console.error(error.stack);
      }
    }
  }

  // Shutdown telemetry
  await shutdownTelemetry();
  console.log("\nDone.");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
