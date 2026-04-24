/**
 * Predefined user action scenarios.
 */

import { ApiClient } from "../api.js";
import { withSpan } from "../telemetry/index.js";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Simulate a user login flow.
 */
export async function loginScenario(client: ApiClient): Promise<void> {
  await withSpan("scenario.login", async () => {
    console.log("  → Recording login action...");
    await client.createAction({
      actionType: "user.login",
      metadata: { method: "password" },
    });

    await sleep(100);

    console.log("  → Recording dashboard view...");
    await client.createAction({
      actionType: "user.view_dashboard",
      metadata: { widgets: "5" },
    });
  });
}

/**
 * Simulate an order creation flow.
 */
export async function orderScenario(client: ApiClient): Promise<void> {
  await withSpan("scenario.order", async () => {
    console.log("  → Viewing product catalog...");
    await client.createAction({
      actionType: "product.view_catalog",
      metadata: { category: "electronics" },
    });

    await sleep(200);

    console.log("  → Adding item to cart...");
    await client.createAction({
      actionType: "cart.add_item",
      metadata: { product_id: "prod-001", quantity: "2" },
    });

    await sleep(100);

    console.log("  → Creating order...");
    const order = await client.createOrder({
      items: [
        {
          productId: "prod-001",
          productName: "Wireless Headphones",
          quantity: 2,
          unitPrice: 79.99,
        },
        {
          productId: "prod-002",
          productName: "USB-C Cable",
          quantity: 3,
          unitPrice: 12.99,
        },
      ],
      notes: "Gift wrap please",
    });

    console.log(`  → Order created: ${order.id} ($${order.totalAmount})`);
    if (order.traceId) {
      console.log(`     Trace ID: ${order.traceId}`);
    }

    await sleep(100);

    console.log("  → Confirming order view...");
    await client.createAction({
      actionType: "order.view",
      metadata: { order_id: order.id },
    });
  });
}

/**
 * Simulate a browsing/search flow.
 */
export async function browseScenario(client: ApiClient): Promise<void> {
  await withSpan("scenario.browse", async () => {
    console.log("  → Searching products...");
    await client.createAction({
      actionType: "product.search",
      metadata: { query: "wireless charger", results: "12" },
    });

    await sleep(150);

    console.log("  → Viewing product details...");
    await client.createAction({
      actionType: "product.view",
      metadata: { product_id: "prod-003" },
    });

    await sleep(100);

    console.log("  → Reading reviews...");
    await client.createAction({
      actionType: "product.view_reviews",
      metadata: { product_id: "prod-003", page: "1" },
    });

    await sleep(200);

    console.log("  → Comparing products...");
    await client.createAction({
      actionType: "product.compare",
      metadata: { product_ids: "prod-003,prod-004,prod-005" },
    });
  });
}

/**
 * Run all scenarios in sequence.
 */
export async function allScenarios(client: ApiClient): Promise<void> {
  console.log("\n--- Login Scenario ---");
  await loginScenario(client);

  console.log("\n--- Browse Scenario ---");
  await browseScenario(client);

  console.log("\n--- Order Scenario ---");
  await orderScenario(client);
}

export const scenarios: Record<
  string,
  (client: ApiClient) => Promise<void>
> = {
  login: loginScenario,
  order: orderScenario,
  browse: browseScenario,
  all: allScenarios,
};
