import InstTable
import TokenTable
import SymbolTable
import LiteralTable


class Assembler:
    """
    Assembler 프로그램의 메인 클래스
    """
    def __init__(self):
        # 기계 명령어 정보를 저장하는 공간
        self.instTable = InstTable.InstTable()
        # 프로그램을 라인별로 저장하는 공간
        self.lineList = []
        # 프로그램의 정보를 section별로 저장하는 공간
        self.tokenList = []
        # 프로그램의 전체 SYMTAB을 section별로 저장하는 공간
        self.symtabList = []
        # 프로그램의 전체 LITTAB을 저장하는 공간
        self.littabList = []
        # 최종적으로 생성된 object code를 저장하는 공간
        self.codeList = []

    def loadinputfile(self, inputfile):
        """
        인자로 받아온 파일을 열어 lineList에 저장한다.

        :param inputfile: 프로그램이 저장되어있는 파일명
        """
        f = open(inputfile, 'r')
        self.lineList = f.read().splitlines()
        f.close()

    def pass1(self):
        """
        pass1의 과정을 수행한다.
        1) 프로그램 소스를 스캔하여 토큰 단위로 분리한 뒤 section별로 tokenList에 저장
        2) 주소를 할당하고 SYMTAB과 LITTAB 생성
        """
        section = -1
        locctr = 0
        # 한 줄씩 읽어나가며 tokenList에 저장
        for line in self.lineList:
            temp = line.split("\t")
            # 주석 생략
            if temp[0] == ".":
                continue
            # section별로 구분하여 저장
            if temp[1] == "START" or temp[1] == "CSECT":
                if temp[1] == "CSECT":
                    self.tokenList[section].tokenList[0].byteSize = locctr
                section += 1
                locctr = 0
                self.symtabList.append(SymbolTable.SymbolTable())
                self.littabList.append(LiteralTable.LiteralTable())
                self.tokenList.append(TokenTable.TokenTable(self.symtabList[section],
                                                            self.littabList[section], self.instTable))
            self.tokenList[section].puttoken(line, locctr)
            # symbol 저장
            if len(temp[0]) > 0:
                self.tokenList[section].symtab.putsymbol(temp[0], locctr)
            # literal 임시 저장
            if len(temp) > 2:
                if temp[2].startswith("="):
                    self.tokenList[section].littab.putliteral(temp[2], locctr)
            # 주소계산
            if self.instTable.instMap.get(temp[1].replace("+", "")) is not None:
                locctr += self.instTable.instMap[temp[1].replace("+", "")].format
                if temp[1].startswith("+"):
                    locctr += 1
            elif temp[1] == "RESB":
                locctr += int(temp[2])
            elif temp[1] == "RESW":
                locctr += int(temp[2]) * 3
            elif temp[1] == "BYTE":
                # X인 경우
                if temp[2].startswith("X"):
                    locctr += int((len(temp[2]) - 3) / 2)
                # C인 경우
                else:
                    locctr += len(temp[2]) - 3
            elif temp[1] == "WORD":
                locctr += 3
            # literal 주소 할당
            elif temp[1] == "LTORG" or temp[1] == "END":
                for literal in self.littabList[section].littab.keys():
                    self.littabList[section].modifyliteral(literal, locctr)
                    if literal.startswith("=X"):
                        locctr += int((len(literal) - 4) / 2)
                    else:
                        locctr += len(literal) - 4
            # EQU 값 계산
            elif temp[1] == "EQU" and temp[2] != "*":
                symbol = temp[2].split("-")
                # 다항(-)이면
                if len(symbol) > 1:
                    addr1 = self.symtabList[section].symtab.get(symbol[0])
                    addr2 = self.symtabList[section].symtab.get(symbol[1])
                    if addr1 is not None and addr2 is not None:
                        self.tokenList[section].symtab.modifysymbol(temp[0], addr1 - addr2)
                    else:
                        self.tokenList[section].symtab.modifysymbol(temp[0], 0)
                # 단항이면
                else:
                    addr = self.symtabList[section].symtab.get(symbol[0])
                    if addr is not None:
                        self.tokenList[section].symtab.modifysymbol(temp[0], addr)
                    else:
                        self.tokenList[section].symtab.modifysymbol(temp[0], 0)
        self.tokenList[section].tokenList[0].byteSize = locctr

    def printsymboltable(self, filename):
        """
        pass1을 통하여 생성된 symtabList를 파일에 저장한다.

        :param filename: SYMTAB 정보를 출력할 파일명
        """
        f = open(filename, 'w')
        for symtab in self.symtabList:
            for symbol in symtab.symtab:
                f.write(str("%-6s\t%04X\n" % (symbol, symtab.symtab[symbol])))
            f.write("\n")
        f.close()

    def printliteraltable(self, filename):
        """
        pass1을 통하여 생성된 littabList를 파일에 저장한다.

        :param filename: LITTAB 정보를 출력할 파일명
        """
        f = open(filename, 'w')
        for littab in self.littabList:
            for literal in littab.littab:
                location = littab.littab[literal]
                literal = literal.replace("=C", "").replace("=X", "").replace("'", "")
                f.write(str("%-6s\t%04X\n" % (literal, location)))
        f.close()

    def pass2(self):
        """
        pass2의 과정을 수행한다.
        1) 분석된 내용을 바탕으로 object code를 생성하여 codeList에 저장
        """
        for section in self.tokenList:
            for i in range(0, len(section.tokenList)):
                section.makeobjectcode(i)
        self.makecodelist()

    def makecodelist(self):
        """
        생성된 object code를 형식에 맞추어 codeList에 저장한다.
        """
        for section in self.tokenList:
            index = 0
            # 레코드 생성
            for i in range(0, len(section.tokenList)):
                if i < index:
                    continue
                token = section.tokenList[i]
                if token.record in ['H', 'D', 'R', 'M', 'E']:
                    self.codeList.append(str("%c%s\n" % (token.record, token.objectCode)))
                    index += 1
                elif token.record == 'T':
                    locctr = token.location + token.byteSize
                    length = token.byteSize
                    # 길이를 먼저 계산하고
                    for index in range(i + 1, len(section.tokenList)):
                        token = section.tokenList[index]
                        if token.record == 0:
                            continue
                        elif token.record != 'T':
                            break
                        if token.location != locctr:
                            break
                        if length + token.byteSize > 0x1E:
                            break
                        locctr += token.byteSize
                        length += token.byteSize
                    token = section.tokenList[i]
                    # 길이만큼 T record 생성
                    objectcode = str("%c%06X%02X" % (token.record, token.location, int(length)))
                    for j in range(i, index):
                        objectcode += str("%s" % section.tokenList[j].objectCode)
                    self.codeList.append(objectcode + "\n")
            self.codeList.append("\n")

    def printobjectcode(self, filename):
        """
        생성된 codeList를 바탕으로 object program을 만들어 파일에 저장한다.

        :param filename: object program을 출력할 파일명
        """
        f = open(filename, 'w')
        for objectcode in self.codeList:
            f.write(objectcode)
        f.close()


"""
메인 루틴
"""
a = Assembler()
a.instTable.openfile("inst.data")
a.loadinputfile("input.txt")
a.pass1()
a.printsymboltable("symtab_20160290.txt")
a.printliteraltable("littab_20160290.txt")
a.pass2()
a.printobjectcode("output_20160290.txt")
