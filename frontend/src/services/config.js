// Endereço do backend.
// - Desenvolvimento: vazio; o Vite redireciona /api para http://127.0.0.1:8000.
// - Publicação: VITE_API_URL=https://<backend>.onrender.com, definido no
//   momento do build (npm run build).
export const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");
