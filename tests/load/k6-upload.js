import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 100,
  duration: '1m',
  thresholds: {
    http_req_failed: ['rate<0.001'],
    http_req_duration: ['p(99)<500'],
  },
};

export default function () {
  const payload = {
    tenant_id: 'load_test',
    formats: 'webp',
    file: http.file(open('./fixtures/sample.jpg', 'b'), 'sample.jpg', 'image/jpeg'),
  };
  const res = http.post('http://localhost:8900/v1/images/upload', payload, { headers: { 'X-Image-API-Key': 'dev-key' } });
  check(res, { 'ready or queued': (r) => [200, 202].includes(r.status) });
}
