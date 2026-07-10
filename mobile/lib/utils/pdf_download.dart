import 'pdf_download_stub.dart' if (dart.library.html) 'pdf_download_web.dart' as impl;

void downloadPdfBytes(List<int> bytes, String filename) {
  impl.downloadPdfBytes(bytes, filename);
}
