/**
 * Type definitions for the OTel demo simulator.
 */

export interface UserContext {
  userId: string;
  orgId: string;
  sessionId: string;
}

export interface ActionRequest {
  actionType: string;
  metadata?: Record<string, string>;
}

export interface ActionResponse {
  id: string;
  actionType: string;
  timestamp: string;
  traceId?: string;
}

export interface OrderItemRequest {
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
}

export interface OrderRequest {
  items: OrderItemRequest[];
  notes?: string;
}

export interface OrderResponse {
  id: string;
  status: string;
  totalAmount: number;
  createdAt: string;
  traceId?: string;
}

export interface ScenarioConfig {
  name: string;
  description: string;
  steps: ScenarioStep[];
}

export interface ScenarioStep {
  name: string;
  action: () => Promise<void>;
  delayMs?: number;
}

export interface SimulatorOptions {
  apiUrl: string;
  scenario: string;
  count: number;
  userId?: string;
  orgId?: string;
  verbose: boolean;
}
