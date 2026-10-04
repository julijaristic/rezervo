"""Izuzetci servisnog sloja - API ih mapira na HTTP status."""


class ReservationError(Exception):
    """Bazni izuzetak za rezervacije."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class VenueNotFoundError(ReservationError):
    """Lokal nije pronađen."""

    pass


class ReservationValidationError(ReservationError):
    """Neispravni podaci za rezervaciju (sto ne pripada lokalu, kapacitet, vreme, itd.)."""

    pass


class ReservationNotFoundError(ReservationError):
    """Rezervacija nije pronađena."""

    pass


class ReservationForbiddenError(ReservationError):
    """Korisnik nema pravo na ovu rezervaciju (npr. nije vlasnik)."""

    pass
