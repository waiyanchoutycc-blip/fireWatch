import {defineConfig} from 'vite';
export default defineConfig({build:{rollupOptions:{output:{manualChunks:{maplibre:['maplibre-gl'],leaflet:['leaflet'],react:['react','react-dom'],geo:['@turf/turf']}}}}});
