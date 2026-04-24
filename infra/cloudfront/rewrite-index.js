// CloudFront Function — runs at viewer-request stage on every cache miss.
//
// Next.js static export writes pages as `<route>/index.html`, but CloudFront's
// `default_root_object` only resolves `/`, not subpaths. Without this rewrite:
//   /chat        → S3 has no object at that key → 403 (AccessDenied XML)
//   /chat/       → same
//   /chat/index.html → 200 (works)
//
// We append `/index.html` (or `index.html` if the path already ends with `/`)
// for any path that doesn't look like a static asset (i.e. has no file extension).
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    if (uri.endsWith('/')) {
        request.uri += 'index.html';
    } else if (!uri.includes('.')) {
        request.uri += '/index.html';
    }

    return request;
}
