import { memo, useEffect, useMemo, useRef } from 'react';
import L from 'leaflet';
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet';

const OSM_TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

// Mesmas cores do restante da interface (styles.css). Os estilos ficam fora do
// componente: o react-leaflet só reaplica um estilo quando o objeto muda.
const streetStyle = { color: '#8c96a1', weight: 2, opacity: 0.5 };
const boundaryStyle = { color: '#d9534f', weight: 2, dashArray: '6 6' };
const vertexStyle = { color: '#8c96a1', weight: 1, fillColor: '#ffffff', fillOpacity: 1 };
const bestStyle = { color: '#397bc5', weight: 5, opacity: 0.94 };
const currentStyle = { color: '#a3acb6', weight: 3, opacity: 0.8, dashArray: '6 6' };

const icons = new Map();

/** Marcador redondo com rótulo (ordem da entrega ou "B"), criado uma vez por rótulo. */
function stopIcon(label, isBase) {
  const key = `${isBase}:${label}`;
  if (!icons.has(key)) {
    const size = isBase ? 30 : 24;
    icons.set(key, L.divIcon({ className: isBase ? 'stop stop-base' : 'stop', html: label, iconSize: [size, size] }));
  }
  return icons.get(key);
}

/** Enquadra o mapa quando a cidade muda (e não a cada nova execução). */
function FitBounds({ bounds }) {
  const map = useMap();
  const fitted = useRef('');
  useEffect(() => {
    const key = bounds.toBBoxString();
    if (key !== fitted.current) {
      fitted.current = key;
      map.fitBounds(bounds, { padding: [16, 16] });
    }
  }, [map, bounds]);
  return null;
}

/** Ruas, limite do bairro e vértices: não mudam durante a animação. */
const StreetLayer = memo(function StreetLayer({ data, onSelectBase }) {
  const streets = data.edges.map(([u, v]) => [data.positions[u], data.positions[v]]);
  return <>
    <Polyline positions={streets} pathOptions={streetStyle} />
    {data.boundary.length > 0 && <Polyline positions={data.boundary} pathOptions={boundaryStyle} />}
    {data.positions.map((position, vertex) => (
      <CircleMarker key={vertex} center={position} radius={5} pathOptions={vertexStyle} eventHandlers={{ click: () => onSelectBase?.(vertex) }}>
        <Tooltip>Vértice {vertex}{onSelectBase ? ' · clique para escolher a base' : ''}</Tooltip>
      </CircleMarker>
    ))}
  </>;
});

/**
 * Mapa interativo (zoom, arrastar e dicas ao passar o mouse) com as rotas de um passo do SA.
 * O bairro real usa os tiles do OpenStreetMap; a grade sintética, que não tem geografia,
 * é desenhada num plano (CRS.Simple).
 */
export default function RouteMap({ data, step, selectedBase, onSelectBase }) {
  const bounds = useMemo(() => L.latLngBounds(data.positions), [data.positions]);
  const line = (path) => path.map((vertex) => data.positions[vertex]);
  const visits = step.bestOrder.map((index) => data.deliveries[index - 1]);
  return (
    <MapContainer
      key={data.geographic ? 'geographic' : 'plane'} // o CRS só muda remontando o mapa
      className="leaflet-map"
      bounds={bounds}
      crs={data.geographic ? L.CRS.EPSG3857 : L.CRS.Simple}
      minZoom={data.geographic ? 13 : -2}
      maxZoom={data.geographic ? 19 : 8}
      zoomSnap={0.25}
    >
      <FitBounds bounds={bounds} />
      {data.geographic && (
        <TileLayer
          url={OSM_TILES}
          maxZoom={19}
          opacity={0.75}
          attribution={`<a href="https://www.openstreetmap.org/copyright">${data.attribution}</a>`}
        />
      )}
      <StreetLayer data={data} onSelectBase={onSelectBase} />
      <Polyline positions={line(step.bestPath)} pathOptions={bestStyle} />
      <Polyline positions={line(step.currentPath)} pathOptions={currentStyle} />
      {visits.map((vertex, index) => (
        <Marker key={vertex} position={data.positions[vertex]} icon={stopIcon(String(index + 1), false)} eventHandlers={{ click: () => onSelectBase?.(vertex) }}>
          <Tooltip direction="top" offset={[0, -12]}>{index + 1}ª entrega · vértice {vertex}</Tooltip>
        </Marker>
      ))}
      <Marker position={data.positions[data.displayBase ?? data.base]} icon={stopIcon('B', true)} zIndexOffset={1000} eventHandlers={{ click: () => onSelectBase?.(data.displayBase ?? data.base) }}>
        <Tooltip direction="top" offset={[0, -15]}>Base exibida · vértice {data.displayBase ?? data.base}</Tooltip>
      </Marker>
      {selectedBase !== null && selectedBase !== undefined && data.positions[selectedBase] && selectedBase !== (data.displayBase ?? data.base) && (
        <Marker position={data.positions[selectedBase]} icon={L.divIcon({ className: 'stop stop-selected', html: 'E', iconSize: [30, 30] })} zIndexOffset={1100}>
          <Tooltip>Base escolhida · vértice {selectedBase}</Tooltip>
        </Marker>
      )}
    </MapContainer>
  );
}
