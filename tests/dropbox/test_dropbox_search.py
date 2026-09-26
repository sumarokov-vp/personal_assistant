from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.search.dropbox_search import DropboxSearch


def test_search_finds_itinerary_pdf(boundary: DropboxBoundary):
    result = DropboxSearch(boundary).find("itinerary")

    assert [hit.path for hit in result.hits] == [
        "Itinerary_ALA_CNX_12-11-2026_000000000000.pdf"
    ]
    assert result.hits[0].size > 0


def test_search_matches_all_words_across_path(boundary: DropboxBoundary):
    result = DropboxSearch(boundary).find("PERSONAL passport")

    assert [hit.path for hit in result.hits] == [
        "03_home/01_personal_docs/passport.txt"
    ]


def test_search_never_returns_closed_entries(boundary: DropboxBoundary):
    search = DropboxSearch(boundary)

    for query in ("secret", "egov", "contract", "probe", "copy", "vault"):
        assert search.find(query).total == 0, query


def test_search_shows_key_file_by_name(boundary: DropboxBoundary):
    assert [hit.path for hit in DropboxSearch(boundary).find("p12").hits] == [
        "03_home/07_ecp/backup_AUTH.P12"
    ]


def test_search_limits_hits_and_reports_total(boundary: DropboxBoundary):
    result = DropboxSearch(boundary).find("03_home", limit=2)

    assert len(result.hits) == 2
    assert result.total > 2
    assert result.hits[0].path == "03_home"
    assert result.hits[0].is_folder
