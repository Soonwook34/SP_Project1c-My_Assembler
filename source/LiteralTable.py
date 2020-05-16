class LiteralTable:
    """
    LITTAB을 저장하는 클래스
    section별로 인스턴스가 하나씩 할당된다.
    """
    def __init__(self):
        # LITTAB
        self.littab = dict()

    def putliteral(self, literal, location):
        """
        literal을 LITTAB에 추가한다.

        :param symbol: 추가할 literal
        :param location: 추가할 literal의 임시 주소
        """
        # 중복 방지
        if self.littab.get(literal) is None:
            self.littab[literal] = location

    def modifyliteral(self, literal, location):
        """
        literal을 주소를 해당 location으로 수정한다.

        :param literal: 주소를 수정할 literal
        :param location: 수정할 literal의 주소
        """
        self.littab[literal] = location
