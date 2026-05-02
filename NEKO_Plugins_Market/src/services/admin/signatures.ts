import { post, request } from "@/services/api";
import type { ServerKeyPair } from "./types";

export function getSignatureKeys() {
  return request<ServerKeyPair[]>("/admin/signatures/keys");
}

export function getDefaultPublicKey() {
  return request<ServerKeyPair>("/signatures/public-keys/default");
}

export function createSignatureKey(name: string, setAsDefault: boolean) {
  return post<ServerKeyPair & { message: string }>("/admin/signatures/keys", {
    name,
    set_as_default: setAsDefault
  });
}

export function deactivateSignatureKey(keypairId: number) {
  return post<{ message: string }>(`/admin/signatures/keys/${keypairId}/deactivate`);
}
