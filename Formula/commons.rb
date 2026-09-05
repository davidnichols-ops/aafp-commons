# Homebrew wrapper formula for AAFP Commons.
#
# This is a PRIVATE, UNPUBLISHED wrapper formula. It is NOT published to a
# Homebrew tap and is NOT installable from any public source. It wraps the
# aafp-commons Python package from the private git repository.
#
# Stable install is BLOCKED: no public release tarball exists. The stable url
# is a placeholder using the RFC 2606 reserved .invalid domain and an all-zero
# sha256; `brew install commons` will fail by design.
#
# Head install (private git over SSH):
#   brew install --HEAD commons
#
# Requires read access to github.com/davidnichols-ops/aafp-commons and a
# working GitHub SSH key (`ssh -T git@github.com` must succeed).
#
# See contracts/T1-brew.md for the full contract.

class Commons < Formula
  include Language::Python::Virtualenv

  desc "Signed, evidence-aware collective memory for software agents"
  homepage "https://github.com/davidnichols-ops/aafp-commons"
  license "Apache-2.0"
  version "0.1.0"

  # BLOCKED: no public release tarball exists for this private repository.
  # The URL is a placeholder (RFC 2606 .invalid) and the sha256 is all-zero.
  # Stable installs will fail. Use `brew install --HEAD commons` instead.
  stable do
    url "https://example.invalid/aafp-commons-0.1.0.tar.gz"
    sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  end

  # Git-capable SSH URL form. Homebrew clones this via `git clone` over SSH,
  # so the operator needs a registered GitHub SSH key and read access to the
  # private repository.
  head "git@github.com:davidnichols-ops/aafp-commons.git", branch: "main"

  depends_on "python@3.11"

  def install
    # Wrapper install: build a Homebrew-managed virtualenv and pip-install the
    # aafp-commons package from the cloned source tree (head) or staged
    # tarball (stable, currently BLOCKED). pip resolves cbor2 and
    # cryptography from PyPI at install time. The wheel vendors the thin
    # ironclad compatibility surface; no external ironclad package is used.
    venv = virtualenv_create(libexec, "python3.11")
    venv.pip_install_and_link(buildpath)
  end

  def caveats
    <<~EOS
      commons is a private, unreleased wrapper formula. It is NOT published
      to a Homebrew tap and is NOT installable via `brew install commons`
      from any public source.

      Head install (private git over SSH):
        brew install --HEAD commons

      Requirements:
        - Read access to github.com/davidnichols-ops/aafp-commons
        - A working GitHub SSH key (`ssh -T git@github.com` must succeed)
        - The head URL uses the git-capable SSH form git@github.com:...

      Stable install is BLOCKED: no public tarball exists. The stable url is
      a placeholder (https://example.invalid/...) and will fail by design.

      The installed console scripts are `commons` and `aafp-commons`. Set
      COMMONS_HOME before first use (never use your default home directly):
        export COMMONS_HOME=/tmp/commons-demo
        commons init && commons world

      This formula wraps the Python package; it does not vendor or replace
      the Ironclad signing surface, ledger formats, constitution files, or
      any simulation home. Canonical install docs remain docs/INSTALL.md.
    EOS
  end

  test do
    assert_match "commons", shell_output("#{bin}/commons --help")
  end
end
