import { useEffect, useRef } from "react";

import L from "leaflet";
import "leaflet/dist/leaflet.css";

import "./trip-map.css";

/*
  Mapa (Leaflet + OpenStreetMap) com pontos numerados.
  - points: [{ id, lat, lng, label, title, detail }], só com coordenadas válidas.
  - route: liga os pontos na ordem (trajeto do dia).
  - activeId: ponto destacado (abre o balão e centraliza).
  - onSelect(id): chamado ao clicar em um ponto.
*/
export default function TripMap({
  points,
  route = false,
  activeId = null,
  onSelect,
  label = "Mapa",
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const markersRef = useRef(new Map());
  const onSelectRef = useRef(onSelect);

  onSelectRef.current = onSelect;

  // Cria o mapa uma vez.
  useEffect(() => {
    const map = L.map(containerRef.current, {
      scrollWheelZoom: false,
    });

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    // O mapa pode nascer em um container que ainda está mudando de tamanho.
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Atualiza os pontos e o trajeto.
  const signature = JSON.stringify(points) + route;

  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();
    markersRef.current = new Map();

    if (points.length === 0) {
      map.setView([0, 0], 1);
      return;
    }

    const coordinates = points.map((point) => [point.lat, point.lng]);

    if (route && points.length > 1) {
      L.polyline(coordinates, {
        color: "#bc6b3e",
        weight: 4,
        opacity: 0.85,
      }).addTo(layer);
    }

    for (const point of points) {
      const marker = L.marker([point.lat, point.lng], {
        title: point.title,
        alt: point.title,
        icon: L.divIcon({
          className: "trip-map-marker",
          html: `<span>${escapeHtml(String(point.label))}</span>`,
          iconSize: [34, 34],
          iconAnchor: [17, 17],
          popupAnchor: [0, -18],
        }),
      });

      marker.bindPopup(
        `<strong>${escapeHtml(point.title)}</strong>` +
          (point.detail
            ? `<br><span>${escapeHtml(point.detail)}</span>`
            : ""),
      );
      marker.on("click", () => onSelectRef.current?.(point.id));
      marker.addTo(layer);
      markersRef.current.set(point.id, marker);
    }

    if (coordinates.length === 1) {
      map.setView(coordinates[0], 15);
    } else {
      map.fitBounds(coordinates, { padding: [36, 36], maxZoom: 16 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature]);

  // Destaque do ponto ativo.
  useEffect(() => {
    const map = mapRef.current;
    const marker = markersRef.current.get(activeId);

    for (const [id, item] of markersRef.current) {
      item.getElement()?.classList.toggle("is-active", id === activeId);
    }

    if (map && marker) {
      map.panTo(marker.getLatLng());
      marker.openPopup();
    }
  }, [activeId, signature]);

  return (
    <div
      ref={containerRef}
      className="trip-map"
      role="region"
      aria-label={label}
    />
  );
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
