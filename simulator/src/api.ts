/**
 * API client for the OTel demo backend.
 */

import {
  ActionRequest,
  ActionResponse,
  OrderRequest,
  OrderResponse,
  UserContext,
} from "./types/index.js";
import { getTracePropagationHeaders, withSpan } from "./telemetry/index.js";

export class ApiClient {
  private baseUrl: string;
  private userContext: UserContext;
  private verbose: boolean;

  constructor(baseUrl: string, userContext: UserContext, verbose = false) {
    this.baseUrl = baseUrl.replace(/\/$/, ""); // Remove trailing slash
    this.userContext = userContext;
    this.verbose = verbose;
  }

  private getHeaders(): Record<string, string> {
    return {
      "Content-Type": "application/json",
      "X-User-Id": this.userContext.userId,
      "X-Org-Id": this.userContext.orgId,
      "X-Session-Id": this.userContext.sessionId,
      ...getTracePropagationHeaders(),
    };
  }

  private log(message: string, data?: unknown): void {
    if (this.verbose) {
      console.log(`[API] ${message}`, data ? JSON.stringify(data, null, 2) : "");
    }
  }

  /**
   * Create a user action.
   */
  async createAction(request: ActionRequest): Promise<ActionResponse> {
    return withSpan(
      "api.createAction",
      async () => {
        const url = `${this.baseUrl}/actions`;
        this.log(`POST ${url}`, request);

        const response = await fetch(url, {
          method: "POST",
          headers: this.getHeaders(),
          body: JSON.stringify({
            action_type: request.actionType,
            metadata: request.metadata || {},
          }),
        });

        if (!response.ok) {
          const error = await response.text();
          throw new Error(`API error ${response.status}: ${error}`);
        }

        const data = await response.json();
        this.log(`Response:`, data);

        return {
          id: data.id,
          actionType: data.action_type,
          timestamp: data.timestamp,
          traceId: data.trace_id,
        };
      },
      {
        "action.type": request.actionType,
        "http.method": "POST",
        "http.url": `${this.baseUrl}/actions`,
      }
    );
  }

  /**
   * Get a user action by ID.
   */
  async getAction(actionId: string): Promise<ActionResponse> {
    return withSpan(
      "api.getAction",
      async () => {
        const url = `${this.baseUrl}/actions/${actionId}`;
        this.log(`GET ${url}`);

        const response = await fetch(url, {
          method: "GET",
          headers: this.getHeaders(),
        });

        if (!response.ok) {
          const error = await response.text();
          throw new Error(`API error ${response.status}: ${error}`);
        }

        const data = await response.json();
        this.log(`Response:`, data);

        return {
          id: data.id,
          actionType: data.action_type,
          timestamp: data.timestamp,
        };
      },
      {
        "action.id": actionId,
        "http.method": "GET",
        "http.url": `${this.baseUrl}/actions/${actionId}`,
      }
    );
  }

  /**
   * Create an order.
   */
  async createOrder(request: OrderRequest): Promise<OrderResponse> {
    return withSpan(
      "api.createOrder",
      async () => {
        const url = `${this.baseUrl}/orders`;
        this.log(`POST ${url}`, request);

        const response = await fetch(url, {
          method: "POST",
          headers: this.getHeaders(),
          body: JSON.stringify({
            items: request.items.map((item) => ({
              product_id: item.productId,
              product_name: item.productName,
              quantity: item.quantity,
              unit_price: item.unitPrice,
            })),
            notes: request.notes,
          }),
        });

        if (!response.ok) {
          const error = await response.text();
          throw new Error(`API error ${response.status}: ${error}`);
        }

        const data = await response.json();
        this.log(`Response:`, data);

        return {
          id: data.id,
          status: data.status,
          totalAmount: data.total_amount,
          createdAt: data.created_at,
          traceId: data.trace_id,
        };
      },
      {
        "order.item_count": request.items.length,
        "http.method": "POST",
        "http.url": `${this.baseUrl}/orders`,
      }
    );
  }

  /**
   * Get an order by ID.
   */
  async getOrder(orderId: string): Promise<OrderResponse> {
    return withSpan(
      "api.getOrder",
      async () => {
        const url = `${this.baseUrl}/orders/${orderId}`;
        this.log(`GET ${url}`);

        const response = await fetch(url, {
          method: "GET",
          headers: this.getHeaders(),
        });

        if (!response.ok) {
          const error = await response.text();
          throw new Error(`API error ${response.status}: ${error}`);
        }

        const data = await response.json();
        this.log(`Response:`, data);

        return {
          id: data.id,
          status: data.status,
          totalAmount: data.total_amount,
          createdAt: data.created_at,
        };
      },
      {
        "order.id": orderId,
        "http.method": "GET",
        "http.url": `${this.baseUrl}/orders/${orderId}`,
      }
    );
  }
}
