import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const apiTarget=process.env.NOCURA_API_TARGET||'http://127.0.0.1:8000';
export default defineConfig({plugins:[react()],server:{proxy:{'/api':{target:apiTarget,changeOrigin:true},'/health':{target:apiTarget,changeOrigin:true}}},build:{rollupOptions:{output:{manualChunks:(id)=>id.includes('/three/')?'three':undefined}}}});
