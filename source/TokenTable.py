class TokenTable:
    """
    프로그램 코드를 분석해 최종 코드로 변환하는 과정을 총괄하는 클래스
    section별로 인스턴스가 하나씩 할당된다.
    """
    def __init__(self, symtab, littab, insttab):
        # section의 SYMTAB
        self.symtab = symtab
        # section의 LITTAB
        self.littab = littab
        # 기계 명령어 정보
        self.insttab = insttab
        # 분석한 코드를 라인별로 저장하는 공간
        self.tokenList = []
        # nixbpe 비트연산을 위한 flag
        self.nFlag = 32
        self.iFlag = 16
        self.xFlag = 8
        self.bFlag = 4
        self.pFlag = 2
        self.eFlag = 1

    def puttoken(self, line, locctr):
        """
        코드를 받아 분석하여 tokenList에 추가한다.

        :param line: 분석할 코드
        :param locctr: 코드의 주소
        """
        self.tokenList.append(Token(line, locctr))

    def makeobjectcode(self, index):
        """
        pass2에서 사용되며 저장된 정보를 바탕으로 object code를 생성하여 저장한다.

        :param index: object code를 생성할 tokenList의 index
        """
        token = self.tokenList[index]
        # H record
        if token.operator == "START" or token.operator == "CSECT":
            token.record = 'H'
            token.objectCode = str("%-6s%06X%06X" % (token.label, token.location, token.location + token.byteSize))
        # D record
        elif token.operator == "EXTDEF":
            token.record = 'D'
            for extdef in token.operand:
                token.objectCode += str("%-6s%06X" % (extdef, self.symtab.symtab[extdef]))
        # E record
        elif token.operator == "EXTREF":
            token.record = 'R'
            for extref in token.operand:
                token.objectCode += str("%-6s" % extref)
        # 기계 명령어인 경우 (T record)
        elif self.insttab.instMap.get(token.operator.replace("+", "")) is not None:
            token.record = 'T'
            inst = self.insttab.instMap[token.operator.replace("+", "")]
            displacement = self.setnixbpe(token, inst)  # nixbpe와 displacement 계산
            if token.byteSize == 2:
                token.objectCode = str("%04X" % (((inst.opcode << 4 | token.nixbpe) << 4) | displacement))
            elif token.byteSize == 3:
                token.objectCode = str("%06X" % (((inst.opcode << 4 | token.nixbpe) << 12) | displacement & 0xFFF))
            elif token.byteSize == 4:
                token.objectCode = str("%08X" % (((inst.opcode << 4 | token.nixbpe) << 20) | displacement & 0xFFFFF))
        # literal 할당인 경우 (T record)
        elif token.operator == "LTORG" or token.operator == "END":
            token.record = 'T'
            for literal in self.littab.littab:
                literal = literal.replace("'", "")
                value = 0
                # X인 경우
                if literal.startswith("=X"):
                    token.byteSize = (len(literal) - 2) / 2
                    value = int(literal.replace("=X", ""), 16)
                # C인 경우
                else:
                    literal = literal.replace("=C", "")
                    token.byteSize = len(literal)
                    for char in literal:
                        value = value << 8
                        value |= ord(char)
            token.objectCode = str(("%0" + str(int(token.byteSize * 2)) + "X") % value)
        # BYTE인 경우 (T record)
        elif token.operator == "BYTE":
            token.record = 'T'
            info = token.operand[0].replace("'", "")
            value = 0
            # X인 경우
            if info.startswith("X"):
                token.byteSize = int((len(info) - 1) / 2)
                value = int(info.replace("X", ""), 16)
            # C인 경우
            else:
                token.byteSize = int(len(info) - 1)
                info = info.replace("C", "")
                for char in info:
                    value = value << 8
                    value |= ord(char)
            token.objectCode = str(("%0" + str(int(token.byteSize * 2)) + "X") % value)
        # WORD인 경우 (T record)
        elif token.operator == "WORD":
            token.record = 'T'
            token.byteSize = 3
            value = 0
            operand = token.operand[0].split('-')
            # 다항(-)인 경우
            if len(operand) > 1:
                addr1 = self.symtab.symtab.get(operand[0])
                addr2 = self.symtab.symtab.get(operand[0])
                if addr1 is not None and addr2 is not None:
                    value = addr1 - addr2
                # 외부 참조일 경우 (M record 추가)
                else:
                    mtoken = Token("M", -1)
                    mtoken.record = 'M'
                    mtoken.objectCode = str("%06X06+%-6s" % (token.location, operand[0]))
                    self.tokenList.append(mtoken)
                    mtoken = Token("M", -1)
                    mtoken.record = 'M'
                    mtoken.objectCode = str("%06X06-%-6s" % (token.location, operand[1]))
                    self.tokenList.append(mtoken)
                    value = 0
            # 단항인 경우
            else:
                addr = self.symtab.symtab.get(operand[0])
                if addr is not None:
                    value = addr
                # 외부 참조일 경우 (M record 추가)
                else:
                    mtoken = Token("M", -1)
                    mtoken.record = 'M'
                    mtoken.objectCode = str("%06X06+%-6s" % (token.location, operand[0]))
                    self.tokenList.append(mtoken)
            token.objectCode = str(("%0" + str(int(token.byteSize * 2)) + "X") % value)
        # section의 마지막인 경우 (E record)
        if index == len(self.tokenList) - 1 or self.tokenList[index + 1].operator == "":
            etoken = Token("E", -1)
            etoken.record = 'E'
            if self.tokenList[0].operator == "START":
                etoken.objectCode = str("%06X" % self.tokenList[0].location)
            self.tokenList.append(etoken)

    def setnixbpe(self, token, inst):
        """
        token이 기계 명령어인 경우에 호출이 되며 nixbpe 비트를 설정하고 displacement를 리턴한다.

        :param token: nixbpe 비트를 설정할 token
        :param inst: 해당 token의 명령어 정보
        :return: 계산된 displacement
        """
        displacement = 0
        token.byteSize = inst.format
        if token.operator.startswith("+"):
            token.byteSize = 4
        # ni 비트
        # 2-byte format인 경우
        if token.byteSize == 2:
            token.setflag(self.nFlag, 0)
            token.setflag(self.iFlag, 0)
        # 4-byte format인 경우
        elif token.byteSize == 4:
            token.setflag(self.nFlag, 1)
            token.setflag(self.iFlag, 1)
        # 3-byte format인 경우
        else:
            token.setflag(self.nFlag, 1)
            token.setflag(self.iFlag, 1)
            # immediate addressing
            if len(token.operand) > 0 and token.operand[0].startswith("#"):
                token.setflag(self.nFlag, 0)
            # indirect addressing
            elif len(token.operand) > 0 and token.operand[0].startswith("@"):
                token.setflag(self.iFlag, 0)
        # x 비트
        if len(token.operand) > 1 and token.operand[1] == "X":
            token.setflag(self.xFlag, 1)
        # bp 비트
        if token.byteSize == 2:
            rList = ["A", "X", "L", "B", "S", "T", "F", "", "PC", "SW"]
            if len(token.operand) > 1:
                displacement = rList.index(token.operand[1])
            displacement |= rList.index(token.operand[0]) << 4
        else:
            # immediate addressing
            if token.getflag(self.nFlag | self.iFlag) == self.iFlag:
                token.setflag(self.bFlag, 0)
                token.setflag(self.pFlag, 0)
                displacement = int(token.operand[0].replace("#", ""))
            # simple, indirect addressing
            else:
                token.setflag(self.bFlag, 0)
                token.setflag(self.pFlag, 1)
                if token.byteSize == 4:
                    token.setflag(self.pFlag, 0)
                # displacement 계산 (SYMTAB 검색)
                target = self.symtab.symtab.get(token.operand[0].replace("@", ""))
                if target is not None:
                    displacement = target - (token.location + token.byteSize)
                    if abs(displacement) > 0x7FF:
                        token.setflag(self.bFlag, 1)
                        token.setflag(self.pFlag, 0)
                # displacement 계산 (LITTAB 검색)
                else:
                    target = self.littab.littab.get(token.operand[0])
                    if target is not None:
                        displacement = target - (token.location + token.byteSize)
                        if abs(displacement) > 0x7FF:
                            token.setflag(self.bFlag, 1)
                            token.setflag(self.pFlag, 0)
                    # 외부 참조일 경우 (M record 추가)
                    else:
                        token.setflag(self.pFlag, 0)
                        if inst.operandNum > 0:
                            target = token.operand[0].replace("@", "")
                            mtoken = Token("M", -1)
                            mtoken.record = 'M'
                            mtoken.objectCode = str("%06X05+%-6s" % (token.location + 1, target))
                            self.tokenList.append(mtoken)
        # e비트
        if token.byteSize == 4:
            token.setflag(self.eFlag, 1)

        return displacement


class Token:
    """
    라인별 코드를 분석하여 저장하고, 그 정보로 생성되는 object code를 저장하는 클래스
    """
    def __init__(self, line, locctr):
        info = line.split('\t')
        self.location = locctr  # 주소
        self.label = ""         # 라벨
        self.operator = ""      # 연산자
        self.operand = []       # 피연산자
        self.comment = ""       # 주석
        self.nixbpe = 0         # nixbpe 비트
        self.objectCode = ""    # object code
        self.byteSize = 0       # object code의 크기
        self.record = 0         # object code가 속하는 record
        # 코드를 분석하여 저장
        # 코드 분석을 거치지 않고 object code를 위해 직접 추가되는 경우(H, E record)는 locctr이 -1로 생성
        if locctr != -1:
            if len(info) == 4:
                self.comment = info[3]
            if len(info) >= 3:
                self.operand = info[2].split(',')
            if len(info) >= 2:
                self.operator = info[1]
                self.label = info[0]

    def setflag(self, flag, value):
        """
        nixbpe 비트에 해당 flag를 설정한다.

        :param flag: flag를 지정할 nixbpe
        :param value: flag 값 (0 또는 1)
        """
        self.nixbpe |= flag
        if value == 0:
            self.nixbpe -= flag

    def getflag(self, flags):
        """
        nixbpe 비트에 해당 flag를 리턴한다.

        :param flags: 알아볼 flag
        :return nixbpe의 flag 값
        """
        return self.nixbpe & flags
