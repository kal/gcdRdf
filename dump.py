import codecs
import mysql.connector
import datetime
from decimal import *
from urllib import *
from characters import *

class NTriplesWriter:
    def __init__(self, path):
        self.f = codecs.open(path, encoding='ascii', mode='w+')
        self.tripleCount = 0

    def close(self):
        self.f.close()

    def write(self, s, p, o, isLiteral, datatype=None):
        self.f.write("%s %s %s .\n" % (self.serializeUri(s), self.serializeUri(p), self.serializeLiteral(o, datatype) if isLiteral else self.serializeUri(o)))
        self.tripleCount = self.tripleCount + 1

    def serializeUri(self, u):
        return "<%s>" %(u)

    def serializeLiteral(self, l, datatype):
        if (datatype):
            return '"%s"^^<%s>' % (l.encode('unicode_escape'), datatype)
        if (isinstance(l, datetime.date)):
            return '"%d-%d-%d"^^<%s>' % (l.day, l.month, l.year, Datatypes.Date)
        if (isinstance(l, int)):
            return '"%d"^^<%s>' % (l,Datatypes.Int)
        if (isinstance(l, Decimal)):
            return '"%d"^^<%s>' % (l, Datatypes.Decimal)
        return '"%s"' % (l.encode('unicode_escape'))

class Namespace:
    def __init__(self, root):
        self.root = root

    def __getattr__(self, localName):
        return self.root + localName

SchemaOrg = Namespace("http://schema.org")

class Datatypes:
    Root = "http://www.w3.org/2001/XMLSchema-datatypes#"
    Int = Root + "integer"
    Date = Root + "date"
    Decimal = Root + "decimal"

class Historical:
    Root = "http://www.techquila.com/psi/historical/"
    StartDate = Root + "earliestStartDate"
    EndDate = Root + "latestEndDate"

ComicsNs = Namespace("http://www.techquila.com/psi/gcd_schema/")

Rdf = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

class DcTerms:
    Root = "http://purl.org/dc/terms/"
    title = Root + "title"
    publisher = Root + "publisher"
    format = Root + "format"
    isPartOf = Root + "isPartOf"
    identifier = Root + "identifier"

class Foaf:
    Root = "http://xmlns.org/foaf/0.1/"
    homepage = Root + "homepage"
    Person = Root + "Person"
    name = Root + "name"

class GcdExtractor:

    def __init__(self, config):
        self.db = mysql.connector.connect(**config)
        self.cursor = self.db.cursor()
        self.individuals = {}
        self.aliases = {}
        self.genres = {}
        self.resources = {}
        self.appearance_count = 0

    def dump(self, writer):
        #self._dump_brands(writer)
        #self._dump_countries(writer)
        #self._dump_indicia_publishers(writer)
        #self._dump_publishers(writer)
        #self._dump_series(writer)
        #self._dump_issues(writer)
        #self._dump_story_types(writer)
        self._dump_stories(writer)

    def _dump_brands(self, writer):
        s = "SELECT id, name, year_began, year_ended, parent_id FROM gcd_brand ORDER BY id"
        self.cursor.execute(s)
        for row in self.cursor.fetchall():
            brandUri = self._make_uri('brand', row[0])
            writer.write( brandUri, Rdf.type, ComicsNs.Brand, 0 )
            writer.write( brandUri, Rdf.label, row[1], 1)
            if (row[2]):
                writer.write( brandUri, Historical.StartDate, datetime.date(day=1, month=1, year=row[2]), 1)
            if (row[3]):
                writer.write( brandUri, Historical.EndDate, datetime.date(day=31, month=12, year=row[3]), 1)
            if (row[4]):
                publisherUri = self._make_uri('publisher', row[4])
                writer.write( brandUri, DcTerms.publisher, publisherUri, 0)
    
    def _dump_countries(self, writer):
        s = "SELECT code, name FROM gcd_country ORDER BY code"
        self.cursor.execute(s)
        for row in self.cursor.fetchall():
            countryUri = self._make_uri('country', row[0])
            writer.write( countryUri, Rdf.type, ComicsNs.Country, 0 )
            writer.write( countryUri, Rdf.label, row[1], 1)

    def _dump_indicia_publishers(self, writer):
        s = "SELECT id, name, parent_id, country_id, year_began, year_ended, is_surrogate, notes, url, issue_count FROM gcd_indicia_publisher ORDER BY id"
        self.cursor.execute(s)
        for row in self.cursor.fetchall():
            uri = self._make_uri('indicia_publisher', row[0])
            writer.write( uri, Rdf.type, ComicsNs.IndiciaPublisher, 0 )
            writer.write( uri, Rdf.label, row[1], 1 )
            writer.write( uri, ComicsNs.countryOfIncorporation, self._make_uri('country', row[3]), 0)
            if (row[4]):
                writer.write( uri, Historical.StartDate, datetime.date(day=1, month=1, year=row[4]), 1)
            if (row[5]):
                writer.write( uri, Historical.EndDate, datetime.date(day=31, month=12, year=row[5]), 1)
            if (row[6]):
                writer.write( uri, ComicsNs.masterPublisher, self._make_uri('publisher', row[2]), 0 )
            else:
                writer.write( uri, ComicsNs.publishesOnBehalfOf, self._make_uri('publisher', row[2]), 0)
            if (row[7]):
                writer.write( uri, ComicsNs.notes, row[7], 1)
            if (row[8]):
                writer.write(uri, Foaf.homepage, row[8], 0)

    def _dump_publishers(self, writer):
        s = "SELECT id, name, country_id, year_began, year_ended, notes, url, is_master, parent_id, imprint_count, brand_count, indicia_publisher_count, series_count, issue_count FROM gcd_publisher ORDER BY id"
        self.cursor.execute(s)
        for row in self.cursor.fetchall():
            uri = self._make_uri('publisher', row[0])
            if (row[7]):
                writer.write(uri, Rdf.type, ComicsNs.Publisher, 0)
            if (row[8]):
                writer.write(uri, Rdf.type, ComicsNs.Imprint, 0)
            writer.write(uri, Rdf.label, row[1], 1)
            writer.write(uri, ComicsNs.countryOfIncorporation, self._make_uri('country', row[2]), 0)
            if (row[3]):
                startDate = "31-1-%d" % row[3]
                writer.write( uri, Historical.StartDate, startDate, 1, Datatypes.Date)
            if (row[4]):
                endDate = "31-12-%d" % row[4]
                writer.write( uri, Historical.EndDate, endDate, 1, Datatypes.Date)
            if (row[5]):
                writer.write(uri, ComicsNs.notes, row[5], 1)
            if (row[6]):
                writer.write(uri, Foaf.homepage, row[6], 1)
            if (row[8]):
                writer.write(uri, ComicsNs.masterPublisher, self._make_uri('publisher', row[8]), 0)
            writer.write(uri, ComicsNs.imprintCount, row[9], 1)
            writer.write(uri, ComicsNs.brandCount, row[10], 1)
            writer.write(uri, ComicsNs.indiciaPublisherCount, row[11], 1)
            writer.write(uri, ComicsNs.seriesCount, row[12], 1)
            writer.write(uri, ComicsNs.issueCount, row[13], 1)

    def _dump_series(self, writer):
        s = "SELECT id, name, sort_name, classification_id, format, year_began, year_ended, publication_dates, first_issue_id, last_issue_id, is_current, publisher_id, imprint_id, country_id, language_id, tracking_notes, notes, publication_notes FROM gcd_series ORDER BY id"
        self.cursor.execute(s)
        for row in self.cursor.fetchall():
            uri = self._make_uri('series', row[0])
            writer.write(uri, Rdf.type, SchemaOrg.Series, 0)
            writer.write(uri, SchemaOrg.name, row[1], 1)
            if(row[2]):
                writer.write(uri, ComicsNs.sortName, row[2], 1)
            # TODO: Format properly belongs on issue, not here
            #if (row[4]):
            #    writer.write(uri, DcTerms.format, row[4], 1)
            if (row[5]):
                startDate = "1-1-%d" % row[5]
                writer.write(uri, SchemaOrg.startYear)
            if (row[6]):
                endDate = "31-12-%d" % row[6]
                writer.write(uri, SchemaOrg.endYear)
            if (row[7] and not(row[8])):
                writer.write(uri, ComicsNs.publicationDates, row[7], 1)
            if (row[8]):
                writer.write(uri, ComicsNs.firstIssue, self._make_uri('issue', row[8]), 0)
            if (row[9]):
                writer.write(uri, ComicsNs.lastIssue, self._make_uri('issue', row[9]), 0)
            if (row[10]):
                writer.write(uri, ComicsNs.isCurrent, True, 1)
            if (row[11]):
                writer.write(uri, SchemaOrg.publisher, self._make_uri('publisher', row[11]),0)
            if (row[12]):
                writer.write(uri, SchemaOrg.imprint, self._make_uri('imprint', row[12]), 0)
            if (row[13]):
                writer.write(uri, ComicsNs.countryOfPublication, self._make_uri('country', row[13]), 0)
            if (row[14]):
                self._dump_tracking_notes(uri, row[14])
            if (row[15]):
               writer.write(uri, ComicsNs.notes, row[15], 1)
            if (row[16]):
                writer.write(uri, ComicsNs.publicationNotes, row[16], 1)

    def _dump_tracking_notes(self, uri, trackingNotes):
        # For now just going to record tracking notes as text
        writer.write(uri, ComicsNs.trackingNotes, trackingNotes, 1)
        return

    def _dump_issues(self, writer):
        s = "SELECT id, number, volume, display_volume_with_number, series_id, indicia_publisher_id, brand_id, publication_date, sort_code, price, page_count, indicia_frequency, editing, notes, isbn, valid_isbn, variant_of_id, variant_name, barcode, title, on_sale_date FROM gcd_issue ORDER BY id"
        self.cursor.execute(s)
        for row in self.cursor.fetchall():
            uri = self._make_uri('issue', row[0])
            writer.write(uri, Rdf.type, SchemaOrg.ComicIssue, 0)
            if (row[1]):
                writer.write(uri, SchemaOrg.issueNumber, row[1], 1)
                if (row[3]):
                    writer.write(uri, ComicsNs.displayIssueNumber, row[2] + '#' + row[1], 1)
                else:
                    writer.write(uri, ComicsNs.displayIssueNumber, row[1], 1)
            if (row[2]):
                writer.write(uri, SchemaOrg.volume, row[2], 1) # Note schema.org says this properly belongs on the series
            if (row[4]):
                writer.write(uri, SchemaOrg.series, self._make_uri('series', row[4]), 0)
            if (row[5]):
                writer.write(uri, SchemaOrg.publisher, self._make_uri('indicia_publisher', row[5]), 0)
            if (row[6]):
                writer.write(uri, ComicsNs.issueBrand, self._make_uri('brand', row[6]), 0)
            if (row[7]):
                writer.write(uri, SchemaOrg.datePublished, row[7], 1)
            if (row[8]):
                writer.write(uri, ComicsNs.sortCode, row[8], 1)
            if (row[9] and row[9] <> "none" and row[9] <> "[none]"):
                offerBNode = '_:issue_offer_' + row[0]
                writer.write(uri, SchemaOrg.offer, offerBNode)
                writer.write(offerBNode, SchemaOrg.name, 'Cover Price')
                writer.write(offerBNode, SchemaOrg.price, row[9])
            if (row[10]):
                writer.write(uri, SchemaOrg.numberOfPages, row[10], 1)
            if (row[11]):
                writer.write(uri, ComicsNs.indiciaFrequency, row[11], 1)
            if (row[12]):
                writer.write(uri, SchemaOrg.editor, row[12], 1)
            if (row[13]):
                writer.write(uri, ComicsNs.notes, row[13], 1)
            # ignoring isbn and just using valid_isbn
            if (row[15]):
                writer.write(uri, SchemaOrg.isbn, row[15], 1) # NOTE: schema.org doesn't currently allow this property on ComicIssue
            if (row[16]):
                writer.write(uri, ComicsNs.variantOf, self._make_uri('issue', row[16]), 0)
                if (row[17]):
                    writer.write(uri, SchemaOrg.variantDescription, row[17], 1)
            if (row[18]):
                writer.write(uri, SchemaOrg.upc, row[18], 1)
            if (row[19]):
                writer.write(uri, SchemaOrg.name, row[19], 1)
            if (row[20]):
                writer.write(uri, ComicsNs.onSaleDate, row[20], 1)

    def _dump_story_types(self, writer):
        s = "SELECT id, name, sort_code FROM gcd_story_type ORDER BY id"
        self.cursor.execute(s)
        for row in self.cursor.fetchall():
            uri = self._make_uri('sequence_type', row[0])
            writer.write(uri, Rdf.type, ComicsNs.SequenceType, 0)
            writer.write(uri, Rdf.label, row[1], 1)
            writer.write(uri, ComicsNs.sortCode, row[2], 1)
        
    def _dump_stories(self, writer):
        s = """SELECT id, title, feature, sequence_number, page_count, 
        issue_id, no_script, script, no_pencils, pencils,
        no_inks, inks, no_colors, colors, no_letters, 
        letters, no_editing, editing, genre, characters, 
        synopsis, reprint_notes, notes, type_id FROM gcd_story"""
        self.cursor.execute(s)
        for row in self.cursor.fetchall():
            uri = self._make_uri('sequence', row[0])
            writer.write(uri, Rdf.type, ComicsNs.Sequence, 0)
            if (row[1]):
                writer.write(uri, DcTerms.title, row[1], 1)
            if (row[2]):
                writer.write(uri, ComicsNs.feature, row[2], 1)
            if (row[3]):
                writer.write(uri, ComicsNs.sequenceNumber, row[3], 1)
            if (row[4]):
                writer.write(uri, ComicsNs.pageCount, row[4], 1)
            if (row[5]):
                writer.write(uri, DcTerms.isPartOf, row[5], 0)
            if (not(row[6])):
                self._write_credits(uri, SchemaOrg.author, row[7])
            if (not(row[8])):
                self._write_credits(uri, SchemaOrg.penciler, row[9])
            if (not(row[10])):
                self._write_credits(uri, SchemaOrg.inker, row[11])
            if (not(row[12])):
                self._write_credits(uri, SchemaOrg.colorist, row[13])
            if (not(row[14])):
                self._write_credits(uri, SchemaOrg.letterer, row[15])
            if (not(row[16])):
                self._write_credits(uri, SchemaOrg.editor, row[17])
            if (row[18]):
                self._write_genres(uri, row[18])
            if (row[19]):
                self._write_characters(uri, row[19])
            if (row[20]):
                writer.write(uri, ComicsNs.synopsis, row[20], 1)
            if (row[21]):
                writer.write(uri, ComicsNs.reprintNotes, row[21], 1)
            if (row[22]):
                writer.write(uri, ComicsNs.notes, row[22], 1)
            if (row[23]):
                writer.write(uri, Rdf.type, self._make_uri('sequence_type', row[23]), 0)

    def _write_credits(self, storyUri, predicateUri, credits):
        for c in credits.split(';'):
            c = c.strip()
            qindex = c.find('[')
            individual = None
            alias = None
            individualUri = None
            aliasUri = None
            if (qindex < 0):
                individual = c
            else:
                individual = c[0:qindex].strip()
                qualifier = c[qindex + 1 : c.find(']')].strip()
                if (qualifier.startswith('as ')):
                    alias = qualifier[3:]
            if (individual == '?'):
                individual = "unknown"
            if (individual.endswith('?')):
                individual = individual[0:-1].strip()
            if (individual.endswith('(?)')):
                individual = individual[0:-3].strip()
            if (alias):
                aliasUri = "http://www.comics/org/individuals/%s/as/%s" % (quote(individual.encode('utf-8'), safe="~"), quote(alias.encode('utf-8'), safe="~"))
            if (individual):
                individualUri = "http://www.comics/org/individuals/%s" % (quote(individual.encode('utf-8'), safe="~"))
            if (alias):
                if (not(aliasUri in self.aliases)):
                    writer.write(aliasUri, Rdf.type, ComicsNs.Pseudonym, 0)
                    writer.write(aliasUri, Rdf.label, alias, 1)
                    writer.write(aliasUri, ComicsNs.pseudonymOf, individualUri, 0)
                    self.aliases[aliasUri] = True
                writer.write(storyUri, predicateUri, aliasUri, 0)
            if (individual):
                if (not (individualUri in self.individuals)):
                    writer.write(individualUri, Rdf.type, Foaf.Person, 0)
                    writer.write(individualUri, Foaf.name, individual, 1)
                    if (not(alias)):
                        writer.write(storyUri, predicateUri, individualUri, 0)
                    

    def _write_genres(self, uri, genres):
        for g in genres.split(';'):
            g = g.strip()
            genreUri = "http://www.comics.org/genres/%s" % (quote(g.lower().encode('utf-8'), safe="~"))
            if (not (genreUri in self.genres)):
                writer.write(genreUri, Rdf.type, ComicsNs.Genre, 0)
                writer.write(genreUri, Rdf.label, g, 1)
            writer.write(uri, SchemaOrg.genre, genreUri, 0)

    def _write_characters(self, uri, characters):
        parser = CharacterParser()
        try:
            for c in parser.parse(characters):
                if c.__class__ == Character:
                    self._write_character_appearance(uri, c)
                elif c.__class__ == CharacterGroup:
                    for m in c.members:
                        self._write_character_appearance_in_group(uri, m, c)
        except ParserError:
            print "Failed to parse characters string: " + characters

        #for c in characters.split(';'):
        #    c = c.strip()
        #    characterUri = "http://www.comics.org/characters/%s" % (quote(c.lower().encode('utf-8'), safe="~"))
        #if (not (characterUri in self.characters)):
        #    writer.write(characterUri, Rdf.type, ComicsNs.Character, 0)
        #    writer.write(characterUri, Rdf.label, c, 1)
        #writer.write(characterUri, ComicsNs.appearsIn, uri, 0)

    def _write_character_appearance(self, sequenceUri, c):
        appearanceBNode = "_:appearance_%d" % self.appearance_count
        self.appearance_count = self.appearance_count + 1
        characterUri = self._assert_character(c.name)
        if (c.alias):
            aliasUri = self._assert_character(c.alias)
        writer.write(characterUri, ComicsNs.appearsIn, sequenceUri, 0)
        writer.write(appearanceBNode, Rdf.type, ComicsNs.Appearance, 0)
        writer.write(appearanceBNode, ComicsNs.sequence, sequenceUri, 0)
        writer.write(appearanceBNode, ComicsNs.character, characterUri, 0)
        if (c.alias):
            writer.write(appearanceBNode, ComicsNs.alias, aliasUri, 0)
        if (c.roles):
            for r in c.roles:
                writer.write(appearanceBNode, ComicsNs.appearanceRole, self._assert_role(r), 0)
        if (c.qualifiers):
            for q in c.qualifiers:
                writer.write(appearanceBNode, ComicsNs.appearanceQualifier, self._assert_qualifier(q),0)
        return appearanceBNode

    def _write_character_appearance_in_group(self, sequenceUri, c, g):
        appearanceBNode = self._write_character_appearance(sequenceUri, c)
        characterUri = self._assert_character(c.name)
        groupUri = self._assert_group(g.name)
        writer.write(appearanceBNode, ComicsNs.group, groupUri, 0)
        writer.write(characterUri, SchemaOrg.memberOf, groupUri, 0)

    def _assert_character(self, characterName):
        return self._assert_named_resource("http://www.comics.org/characters/", characterName, ComicsNs.Character)

    def _assert_role(self, roleName):
        return self._assert_named_resource("http://www.comics.org/roles/", roleName, ComicsNs.Role)

    def _assert_qualifier(self, qualifierName):
        return self._assert_named_resource("http://www.comics.org/qualifiers/", qualifierName, ComicsNs.Qualifier)

    def _assert_group(self, groupName):
        return self._assert_named_resource("http://www.comics.org/groups/", groupName, SchemaOrg.Organization)

    def _assert_named_resource(self, prefix, label, resourceType):
        resourceUri = "%s%s" % (prefix, quote(label.strip().lower().encode('utf-8'), safe="~"))
        if (not (resourceUri in self.resources)):
            writer.write(resourceUri, Rdf.type, resourceType, 0)
            writer.write(resourceUri, Rdf.label, label, 1)
        return resourceUri

    def _make_uri(self, type, id):
        if (isinstance(id, int)):
            return "http://www.comics.org/%s/%d" % (type, id)
        return "http://www.comics.org/%s/%s" % (type, id)

    def close(self):
        self.db.close()

if __name__ == '__main__':
    from config import Config
    config = Config.dbinfo().copy()
    writer = NTriplesWriter('gcd.nt')
    extractor = GcdExtractor(config)
    extractor.dump(writer)
    extractor.close()
    writer.close()
    print "Wrote %d triples" % writer.tripleCount
