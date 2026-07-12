/**
 * frontend/lib/encryption.ts
 * Hybrid AES-256-GCM + RSA-OAEP encryption using native WebCrypto API.
 * No external dependencies required.
 */

const RSA_OAEP_PARAMS: RsaHashedImportParams = {
    name: "RSA-OAEP",
    hash: "SHA-256",
};

const AES_GCM_PARAMS: AesKeyAlgorithm = {
    name: "AES-GCM",
    length: 256,
};

/**
 * Encrypt a payload using hybrid AES+RSA encryption.
 * 1. Generate random AES-256 key
 * 2. Encrypt payload with AES-GCM
 * 3. Encrypt AES key with RSA public key
 * 4. Return { encryptedKey, encryptedData, nonce }
 */
export async function encryptPayload(
    payload: Record<string, unknown>,
    publicKeyPem: string
): Promise<{ encryptedKey: string; encryptedData: string; nonce: string }> {
    // 1. Import RSA public key from PEM
    const publicKey = await importPublicKey(publicKeyPem);

    // 2. Generate random AES-256 key
    const aesKey = await crypto.subtle.generateKey(
        AES_GCM_PARAMS,
        true,
        ["encrypt", "decrypt"]
    );

    // 3. Generate random 12-byte nonce for AES-GCM
    const nonce = crypto.getRandomValues(new Uint8Array(12));

    // 4. Encrypt payload with AES-GCM
    const payloadBytes = new TextEncoder().encode(JSON.stringify(payload));
    const encryptedData = await crypto.subtle.encrypt(
        { name: "AES-GCM", iv: nonce },
        aesKey,
        payloadBytes
    );

    // 5. Export AES key raw bytes
    const aesKeyRaw = await crypto.subtle.exportKey("raw", aesKey);

    // 6. Encrypt AES key with RSA-OAEP
    const encryptedKey = await crypto.subtle.encrypt(
        RSA_OAEP_PARAMS,
        publicKey,
        aesKeyRaw
    );

    // 7. Return base64-encoded values
    return {
        encryptedKey: arrayBufferToBase64(encryptedKey),
        encryptedData: arrayBufferToBase64(encryptedData),
        nonce: arrayBufferToBase64(nonce.buffer),
    };
}

async function importPublicKey(pem: string): Promise<CryptoKey> {
    const pemHeader = "-----BEGIN PUBLIC KEY-----";
    const pemFooter = "-----END PUBLIC KEY-----";
    const pemContents = pem
        .replace(pemHeader, "")
        .replace(pemFooter, "")
        .replace(/\s/g, "");
    const binaryDer = base64ToArrayBuffer(pemContents);

    return crypto.subtle.importKey(
        "spki",
        binaryDer,
        RSA_OAEP_PARAMS,
        false,
        ["encrypt"]
    );
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}
