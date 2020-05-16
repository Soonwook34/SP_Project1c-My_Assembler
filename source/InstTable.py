class InstTable:
    """
    전체 기계 명령어 정보를 저장하는 클래스
    """
    def __init__(self):
        # 기계 명령어 정보
        self.instMap = dict()

    def openfile(self, filename):
        """
        파일에 저장되어있는 기계 명령어 정보를 instMap에 저장한다.

        :param filename: 기계 명령어 정보가 저장되어있는 파일명
        """
        f = open(filename, 'r')
        lines = f.read().splitlines()
        for line in lines:
            inst = Instruction(line)
            self.instMap[inst.instruction] = inst
        f.close()


class Instruction:
    """
    하나의 기계 명령어 정보를 저장하는 클래스
    """
    def __init__(self, line):
        info = line.split('\t')
        self.instruction = info[0]      # 명령어 이름
        self.format = int(info[1])      # 포맷
        self.opcode = int(info[2], 16)  # opcode
        self.operandNum = int(info[3])  # 피연산자 개수
