// Ensure Web Streams globals exist (Node < 18)
import { ReadableStream, WritableStream, TransformStream } from 'stream/web';

const g: any = globalThis as any;

if (typeof g.ReadableStream === 'undefined') {
  g.ReadableStream = ReadableStream;
}
if (typeof g.WritableStream === 'undefined') {
  g.WritableStream = WritableStream;
}
if (typeof g.TransformStream === 'undefined') {
  g.TransformStream = TransformStream;
}
