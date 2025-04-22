from src.services.video_downloader import VideoDownloader
vd = VideoDownloader()
formats = vd.get_available_formats("https://youtu.be/dQw4w9WgXcQ")
for f in formats[:10]:
    print(f.format_id, f.resolution, f.human_size())
vd.shutdown()