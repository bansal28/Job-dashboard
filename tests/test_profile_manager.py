import base64
import pytest

from server import profile_manager


def test_uploaded_latex_becomes_active_resume(tmp_path, monkeypatch):
    default_resume = tmp_path / "default.tex"
    default_resume.write_text("default", encoding="utf-8")
    _patch_profile_paths(monkeypatch, tmp_path, default_resume)

    profile = profile_manager.save_resume_profile(
        latex_filename="resume.tex",
        latex_content=r"\section*{Experience}\item Built APIs.",
    )

    assert profile["source"] == "uploaded"
    assert profile_manager.get_active_resume_path() == tmp_path / "active_resume.tex"
    assert (tmp_path / "active_resume.tex").read_text(encoding="utf-8").endswith("Built APIs.")


def test_single_tex_resume_file_can_seed_profile(tmp_path, monkeypatch):
    default_resume = tmp_path / "default.tex"
    default_resume.write_text("default", encoding="utf-8")
    _patch_profile_paths(monkeypatch, tmp_path, default_resume)
    payload = base64.b64encode(b"\\section*{Projects}\n\\item Shipped a React app.").decode("ascii")

    profile_manager.save_resume_profile(
        resume_filename="profile.tex",
        resume_content_base64=f"data:text/plain;base64,{payload}",
    )

    assert profile_manager.get_active_resume_path().read_text(encoding="utf-8").startswith(r"\section*{Projects}")
    assert (tmp_path / "resume_original.tex").exists()


def test_first_upload_requires_text_resume_source(tmp_path, monkeypatch):
    default_resume = tmp_path / "default.tex"
    default_resume.write_text("default", encoding="utf-8")
    _patch_profile_paths(monkeypatch, tmp_path, default_resume)
    payload = base64.b64encode(b"%PDF-1.4").decode("ascii")

    with pytest.raises(ValueError, match=r"\.tex resume source"):
        profile_manager.save_resume_profile(
            resume_filename="resume.pdf",
            resume_content_base64=f"data:application/pdf;base64,{payload}",
        )

    assert not (tmp_path / "resume_original.pdf").exists()


def _patch_profile_paths(monkeypatch, profile_dir, default_resume):
    monkeypatch.setattr(profile_manager, "PROFILE_DIR", profile_dir)
    monkeypatch.setattr(profile_manager, "PROFILE_META_PATH", profile_dir / "profile.json")
    monkeypatch.setattr(profile_manager, "ACTIVE_RESUME_TEX", profile_dir / "active_resume.tex")
    monkeypatch.setattr(profile_manager, "RESUME_PATH", default_resume)
