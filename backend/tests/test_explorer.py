from app.agents.explorer import article_feed_entries, iso8601_duration, parse_link, youtube_feed_entries, youtube_format

YT_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <title>Canal</title>
 <entry>
  <yt:videoId>abcdefghijk</yt:videoId>
  <title>Python tips explained</title>
  <link rel="alternate" href="https://www.youtube.com/shorts/abcdefghijk"/>
  <author><name>Canal</name></author>
  <published>2026-11-18T10:00:00+00:00</published>
  <media:group>
   <media:thumbnail url="https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg" width="480" height="360"/>
   <media:description>Learn three python tricks</media:description>
  </media:group>
 </entry>
</feed>"""

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Blog</title>
<item><title>New CVE in OpenSSH</title><link>https://example.com/cve</link>
<description>&lt;p&gt;Critical bug &lt;img src="https://example.com/a.jpg"/&gt;&lt;/p&gt;</description>
<pubDate>Wed, 18 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>"""


def test_parse_youtube_feed():
    rows = youtube_feed_entries(YT_FEED)
    assert len(rows) == 1
    r = rows[0]
    assert r["external_id"] == "abcdefghijk"
    assert r["format"] == "short"
    assert r["published_at"].year == 2026
    assert "python" in r["description"].lower()


def test_parse_article_feed():
    rows = article_feed_entries(RSS)
    assert rows[0]["platform"] == "article"
    assert rows[0]["thumbnail_url"] == "https://example.com/a.jpg"
    assert "Critical bug" in rows[0]["description"]


def test_parse_links():
    assert parse_link("https://youtu.be/dQw4w9WgXcQ")["external_id"] == "dQw4w9WgXcQ"
    assert parse_link("https://www.youtube.com/shorts/dQw4w9WgXcQ")["format"] == "short"
    t = parse_link("https://www.tiktok.com/@user/video/7300000000000000000")
    assert t["platform"] == "tiktok" and t["embed_url"].endswith("7300000000000000000")
    ig = parse_link("https://www.instagram.com/reel/Cabc123/")
    assert ig["platform"] == "instagram" and ig["embed_url"].endswith("/embed")
    assert parse_link("https://www.youtube.com/@fireship")["kind"] == "creator"
    assert parse_link("https://example.com/post")["platform"] == "article"


def test_durations():
    assert iso8601_duration("PT1H2M3S") == 3723
    assert iso8601_duration("PT45S") == 45
    assert youtube_format(45) == "short"
    assert youtube_format(600) == "long"
