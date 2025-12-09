// Provide fetch / Request / Response / Headers for Node < 18
import { fetch, Headers, Request, Response } from 'undici';

const g: any = globalThis as any;

if (typeof g.fetch === 'undefined') g.fetch = fetch;
if (typeof g.Headers === 'undefined') g.Headers = Headers;
if (typeof g.Request === 'undefined') g.Request = Request;
if (typeof g.Response === 'undefined') g.Response = Response;
