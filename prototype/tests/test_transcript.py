from prototype.transcript import load_transcript


def test_load_transcript_reads_plain_text(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    content = "user: build the CLI\nassistant: done\nunicode: café\n"
    transcript_path.write_text(content, encoding="utf-8")

    transcript = load_transcript(transcript_path)

    assert transcript.path == transcript_path
    assert transcript.mode == "text"
    assert transcript.content == content
