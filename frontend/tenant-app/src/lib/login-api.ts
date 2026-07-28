import axios from "axios";
import { encryptPayload } from "./encryption";

const http = axios.create({
  baseURL: "/rent/tenant",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

export async function loginByUsername(
  username: string,
  pin: string,
  rememberMe = false
): Promise<{ status: string; redirect_url: string }> {
  const { data: keyRes } = await http.get<{ publicKey: string }>(
    "api/auth/public-key"
  );
  if (!keyRes.publicKey) throw new Error("Failed to load public key");

  const encrypted = await encryptPayload(
    { username, pin, rememberme: rememberMe },
    keyRes.publicKey
  );

  const { data } = await http.post<{ status: string; redirect_url: string }>(
    "api/auth/login-by-username",
    encrypted
  );
  return data;
}
