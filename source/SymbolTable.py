class SymbolTable:
    """
    SYMTAB을 저장하는 클래스
    section별로 인스턴스가 하나씩 할당된다.
    """
    def __init__(self):
        # SYMTAB
        self.symtab = dict()

    def putsymbol(self, symbol, location):
        """
        symbol을 SYMTAB에 추가한다.

        :param symbol: 추가할 symbol
        :param location: 추가할 symbol의 주소
        """
        self.symtab[symbol] = location

    def modifysymbol(self, symbol, location):
        """
        symbol의 주소를 해당 location으로 수정한다.

        :param symbol: 주소를 수정할 symbol
        :param location: 수정할 symbol의 주소
        """
        self.symtab[symbol] = location
