/**
 * OpenTelemetry setup for the simulator.
 *
 * Configures tracing for the frontend simulator to demonstrate
 * end-to-end trace propagation.
 */

import { NodeSDK } from "@opentelemetry/sdk-node";
import { Resource } from "@opentelemetry/resources";
import {
  ATTR_SERVICE_NAME,
  ATTR_SERVICE_VERSION,
} from "@opentelemetry/semantic-conventions";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { trace, context, propagation, SpanKind } from "@opentelemetry/api";

let sdk: NodeSDK | null = null;

export interface TelemetryConfig {
  serviceName?: string;
  serviceVersion?: string;
  otlpEndpoint?: string;
  enabled?: boolean;
}

/**
 * Initialize OpenTelemetry SDK.
 */
export function initTelemetry(config: TelemetryConfig = {}): void {
  const {
    serviceName = "otel-demo-simulator",
    serviceVersion = "1.0.0",
    otlpEndpoint,
    enabled = true,
  } = config;

  if (!enabled) {
    console.log("Telemetry disabled");
    return;
  }

  const resource = new Resource({
    [ATTR_SERVICE_NAME]: serviceName,
    [ATTR_SERVICE_VERSION]: serviceVersion,
    "deployment.environment": "dev",
  });

  // Only add OTLP exporter if endpoint is provided
  const spanProcessors = [];
  if (otlpEndpoint) {
    const exporter = new OTLPTraceExporter({
      url: otlpEndpoint,
    });
    spanProcessors.push(new BatchSpanProcessor(exporter));
  }

  sdk = new NodeSDK({
    resource,
    spanProcessors,
  });

  sdk.start();
  console.log(`Telemetry initialized: ${serviceName} v${serviceVersion}`);
}

/**
 * Shutdown OpenTelemetry SDK.
 */
export async function shutdownTelemetry(): Promise<void> {
  if (sdk) {
    await sdk.shutdown();
    console.log("Telemetry shutdown complete");
  }
}

/**
 * Get a tracer instance.
 */
export function getTracer(name = "simulator") {
  return trace.getTracer(name);
}

/**
 * Create headers for trace propagation.
 */
export function getTracePropagationHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  propagation.inject(context.active(), headers);
  return headers;
}

/**
 * Execute a function within a new span.
 */
export async function withSpan<T>(
  name: string,
  fn: () => Promise<T>,
  attributes?: Record<string, string | number | boolean>
): Promise<T> {
  const tracer = getTracer();

  return tracer.startActiveSpan(
    name,
    { kind: SpanKind.CLIENT },
    async (span) => {
      try {
        if (attributes) {
          for (const [key, value] of Object.entries(attributes)) {
            span.setAttribute(key, value);
          }
        }

        const result = await fn();
        span.setStatus({ code: 1 }); // OK
        return result;
      } catch (error) {
        span.setStatus({
          code: 2, // ERROR
          message: error instanceof Error ? error.message : "Unknown error",
        });
        throw error;
      } finally {
        span.end();
      }
    }
  );
}
