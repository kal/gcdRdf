class Character:
    Roles = ['origin','introduction', 'death', 'cameo', 'villain']
    def __init__(self, name):
        self.name = name.strip()
        self.alias = None
        self.roles = []
        self.qualifiers = []

    def add_role_or_qualifier(self, role_or_qualifier):
        if (role_or_qualifier.lower() in Character.Roles):
            self.roles.append(role_or_qualifier)
        else:
            self.qualifiers.append(role_or_qualifier)

    def __str__(self):
        ret = self.name
        if (self.alias):
            ret = ret + " aka: " + self.alias
        if (len(self.roles) > 0):
            ret = ret + " roles: " + ", ".join(self.roles)
        if (len(self.qualifiers) > 0):
            ret = ret + " qualifiers: " + ", ".join(self.qualifiers)
        return ret

class CharacterGroup:
    def __init__(self, name):
        self.name = name
        self.members = []
    
    def add_member(self, character):
        self.members.append(character)

    def __str__(self):
        ret= 'Group: ' + self.name +' consisting of: '
        for m in self.members:
            ret = ret + str(m) + ", "
        return ret

class CharacterNode:
    def _init_(self):
        self.label = ''
        self.groupOrAlias = []
        self.qualifier = []

class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError

CPTokenTypes = Enum(["Label", "LSB", "RSB", "LPAREN", "RPAREN", "SEMI"])
    
class CPToken:
    def __init__(self, tokenType, stringValue):
        self.tokenType = tokenType
        self.stringValue = stringValue

    def __str__(self):
        if (self.tokenType == CPTokenTypes.Label):
            return self.tokenType + ":'" + self.stringValue + "'"
        return self.tokenType

class ParserError:
    def __init__(self, msg = 'Parser Error'):
        self.msg = msg

    def __str__(self):
        return self.msg

class CharacterParser:
    Separators = {'[' : CPToken(CPTokenTypes.LSB, '['),
                  ']' : CPToken(CPTokenTypes.RSB, ']'),
                  '(' : CPToken(CPTokenTypes.LPAREN, '('),
                  ')' : CPToken(CPTokenTypes.RPAREN, ')'),
                  ';' : CPToken(CPTokenTypes.SEMI, ';')}

    def tokenize(self, s):
        current = ''
        for c in s:
            if c in CharacterParser.Separators:
                if (current.strip()):
                    yield CPToken(CPTokenTypes.Label, current.strip())
                    current = ''
                yield CharacterParser.Separators[c]
            else:
                current = current + c
        if (current):
            current = current.strip()
            if (current):
                yield CPToken(CPTokenTypes.Label, current)

    def parse(self, s):
        self.tokens = list(self.tokenize(s))
        self.current_label = ''
        self.current_character = None
        self.current_group = None
        self.results = []
        self.parse_character_list()
        #print "%s => %s" % (s, self.results)
        return self.results

    def parse_character_list(self):
        while(len(self.tokens) > 0):
            t = self.tokens[0]
            if (t.tokenType == CPTokenTypes.Label):
                if (len(self.tokens) > 1):
                    la = self.tokens[1]
                    if (la.tokenType == CPTokenTypes.SEMI):
                        self.current_character = Character(t.stringValue)
                        self.tokens = self.tokens[1:]
                    elif (la.tokenType == CPTokenTypes.LPAREN):
                        self.current_character = Character(t.stringValue)
                        self.tokens = self.tokens[2:]
                        self.parse_roles_or_qualifier()
                    elif (la.tokenType == CPTokenTypes.LSB):
                        self.current_label = t.stringValue
                        self.tokens = self.tokens[2:]
                        self.parse_character_or_group()
                        if ((len(self.tokens) > 0) and (self.tokens[0].tokenType == CPTokenTypes.LPAREN)):
                            self.tokens = self.tokens[1:]
                            self.parse_roles_or_qualifier()
                    else:
                        raise ParserError('Expected ; ( or [. Got ' + str(la))
                    if (len(self.tokens) == 0):
                        self.notify_character()
                    elif(self.tokens[0].tokenType == CPTokenTypes.SEMI):
                        self.notify_character()
                        self.tokens = self.tokens[1:]
                    elif(self.tokens[0].tokenType == CPTokenTypes.RSB):
                        self.notify_character()
                        self.tokens = self.tokens[1:]
                        if ((len(self.tokens) > 0) and (self.tokens[0].tokenType == CPTokenTypes.SEMI)):
                            self.tokens = self.tokens[1:]
                    else:
                        raise ParserError('Expected ; ] or end of stream. Got : ' + str(self.tokens[0]))
                else:
                    self.current_character = Character(t.stringValue)
                    self.notify_character()
                    self.tokens = self.tokens[1:]
            else:
                raise ParserError('Expected a label. Got ' + str(t))

    def parse_character_or_group(self):
        t = self.tokens[0]
        la = self.tokens[1]
        if (la.tokenType == CPTokenTypes.RSB):
            self.current_character = Character(self.current_label)
            self.current_character.alias = t.stringValue
            self.tokens = self.tokens[2:]
            return
        self.current_group = CharacterGroup(self.current_label)
        self.parse_character_list()
        self.notify_group()
        
    def parse_roles_or_qualifier(self):
        val = self.tokens[0].stringValue
        for role in val.split(','):
            self.current_character.add_role_or_qualifier(role.strip())
        self.tokens = self.tokens[1:]
        if (self.tokens[0].tokenType == CPTokenTypes.RPAREN):
            self.tokens = self.tokens[1:]
        elif(self.tokens[0].tokenType == CPTokenTypes.SEMI):
            self.tokens = self.tokens[1:]
            self.parse_roles_or_qualifier()
        else:
            raise ParserError

    def notify_character(self):
        if (self.current_group):
            self.current_group.add_member(self.current_character)
            self.current_character = None
        else:
            self.results.append(self.current_character)
            self.current_character = None

    def notify_group(self):
        self.results.append(self.current_group)
        self.current_group = None

TestStrings = [
    "Sam Zabel; Mr. Lupicinus; Cynthia; Moxie; Toxie; Tisco",
    "Jimmy Olsen",
    "Jimmy Olsen (origin, death)",
    "Red Tornado [Ma Hunkel] (cameo)",
    "Green Lantern [Hal Jordan]; Green Lantern [Alan Scott] (cameo)",
    "Batman (photo of Adam West)",
    "Justice League of America [Green Lantern [Hal Jordan] (origin); Superman [Clark Kent] (Earth-1)];",
    "Justice Society of America [Superman [Clark Kent] (Earth-2); Flash [Jay Garrick] (cameo)]",
]

if (__name__ == "__main__"):
    parser = CharacterParser()
    for s in TestStrings:
        print 'Input:' + s
        print 'Tokenizing...'
        for t in parser.tokenize(s):
            print t
        print 'Parsing...'
        parser.parse(s)
    

        
