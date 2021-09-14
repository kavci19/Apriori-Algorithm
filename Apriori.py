import operator
import sqlite3 as sql
import pandas
import itertools

from pandas import DataFrame

# here is a dummy comment added to demonstrate editing a branch for advanced swe

class Apriori:

    def __init__(self, min_supp, min_conf):

        self.con, self.cur, self.columns, self.min_rows = self.create_database(min_supp)
        self.k = 1
        self.min_confidence = min_conf
        self.min_support = min_supp
        self.itemset_supports = dict() # maps an itemset to its support


    def create_database(self, min_supp):
        con = sql.connect(":memory:")
        cur = con.cursor()

        # test out toy example
        '''
        d = {'col1': ['pen', 'pen', 'pen', 'pen'], 'col2': ['ink', 'ink', 'diary', 'ink'], 'col3': ['diary', 'diary', 'a', 'soap'], 'col4': ['soap', 'b', 'c', 'd']}
        df = DataFrame(data=d)
        '''

        # first 15,000 rows correspond to complaints in the week from March 8, 2020 to March 16, 2020
        # df = pandas.read_csv(r'C:\Users\kaany\Downloads\311_Service_Requests_from_2010_to_Present.csv', nrows=15000)
        df = pandas.read_csv(r'INTEGRATED-DATASET.csv', nrows=15000)
        df = df.astype(str)



        self.num_rows = df.shape[0]
        min_rows = min_supp * self.num_rows
        print(f'The size of the database is {self.num_rows} rows, so with a min_support of {min_supp}, an itemset must exist '
              f'in at least {min_rows} rows to be above threshold.\n')
        df.to_sql('Complaints', con, if_exists='append', index=False)

        cur.execute("PRAGMA table_info(Complaints)")
        attributes = cur.fetchall()
        columns = []

        # annotate each cell in the database with its column name, so that items do not lose their column name
        # when creating itemsets
        for a in attributes:
            c = a[1]
            columns.append(c)
            command = f'''update Complaints set `{c}` = '{c} = ' || `{c}` '''
            cur.execute(command)


        return con, cur, columns, min_rows


    # generates the SQL statement to create the next L or C table with the appropriate column names
    def get_sql_create_table_statement(self, type):

        if type == 'l':
            command = f'create table L{self.k} ' \
                      f'(id INTEGER primary key AUTOINCREMENT, ' \
                      f'support INTEGER default 0,'

        else:
            command = f'create table C{self.k} ' \
                      f'(id INTEGER primary key AUTOINCREMENT, ' \
                      f'support INTEGER default 0,'


        for i in range(1, self.k+1):
            command += f' item{i} TEXT, '

        command = command[:-2]
        command += ')'


        print(f'Create table Statement: {command}\n\n')
        return command



    # creates the sql statement to generate the candidate table C_k based off of the columns of L_{k-1}
    def get_sql_candidate_table_statement(self):

        command = f'insert into C{self.k} '

        command += '('

        for i in range(1, self.k+1):
            command += f'item{i}, '

        command = command[:-2]
        command += ') select '

        for i in range(1, self.k):
            command += f'A.item{i}, '

        command += f'B.item{self.k-1} from L{self.k-1} A join L{self.k-1} B where '

        for i in range(1, self.k-1):
            command += f'A.item{i} == B.item{i} and '

        command += f'A.item{self.k-1} < B.item{self.k-1}'

        print(f'Statement used to create C{self.k}: {command}\n\n')

        return command



    # creates a set of single items from the original database by scanning through each row and column and making each
    # cell its own item. then, creates C1 by making a row for each item
    def get_single_itemsets(self):
        items = set()
        cur = self.cur

        command = self.get_sql_create_table_statement('c')
        cur.execute(command)

        cur.execute('select * from Complaints')
        rows = cur.fetchall()
        for row in rows:
            for i in range(len(row)):

                item = row[i]
                # skip meaningless items
                if item in ['Location Type = nan', 'Street Name = nan', 'Borough = Unspecified']:
                    continue
                items.add(item)

        for item in items:
            cur.execute('insert into C1 (item1, support) values (:i, 0)', {'i': item})



        cur.execute('select * from C1')
        print('C1:')
        for row in cur.fetchall():
            print(row)
        print('\n\n')

        return


    # generates C_k, the candidate table for C, by joining L_{k-1} with itself where every item is equal except
    # the last
    def get_candidates(self):

        cur = self.cur
        command = self.get_sql_create_table_statement('c')
        cur.execute(command)
        command = self.get_sql_candidate_table_statement()
        cur.execute(command)

        print(f'C{self.k}:')
        cur.execute(f'select * from C{self.k}')
        for row in cur.fetchall():
            print(row)
        print('\n\n')


        return


    # checks if an item basket is a subset of a row in the original database
    def is_subset(self, A, B):

        return set(A).issubset(set(B))



    # finds the support for each item in C_k by looping through each row in the database and checking which itemsets
    # in C are subsets of the row in the original database
    def update_candidate_supports(self):

        cur = self.cur

        cur.execute('select * from Complaints')
        database_rows = cur.fetchall()
        cur.execute(f'select * from C{self.k}')
        candidate_rows = cur.fetchall()

        for db_row in database_rows:
            for candidate in candidate_rows:
                candidate_key = candidate[0]
                candidate = candidate[2:]
                # print(f'Checking if {candidate} is a subset of {db_row}')
                if self.is_subset(candidate, db_row):
                    cur.execute(f'''update C{self.k} 
                    set support = support + 1 
                    where id = :key''', {'key': candidate_key})


        cur.execute(f'select * from C{self.k}')
        print(f'C{self.k} after finding supports: ')
        for item in cur.fetchall():
            print(item)
        print('\n\n')

        return



    # creates L_k and populates it with itemsets (rows) in C_k that have support above the given threshold
    def prune(self):

        cur = self.cur
        command = self.get_sql_create_table_statement('l')
        cur.execute(command)

        cur.execute(f'''insert into L{self.k} select * from C{self.k} where support >= {self.min_rows}''')
        cur.execute(f'select * from L{self.k}')
        print(f'L{self.k} after pruning C{self.k}:')
        for row in cur.fetchall():
            print(row)
            itemset = frozenset(row[2:])
            support = int(row[1])
            self.itemset_supports[itemset] = support

        print('\n\n')

        self.k += 1


        return


    # retrieves the number of rows in C_k
    def get_C_size(self):

        cur = self.cur
        cur.execute(f'select count(*) from C{self.k}')
        count = cur.fetchone()[0]
        print(f'Size of C{self.k}: {count}')
        print('\n\n\n')
        return count


    # calculates the confidence of an association rule by looking up the support of the LHS and union of LHS-RHS
    # in the support dictionary. Applies the formula: confidence = support[union] / support[LHS]
    def get_confidence(self, LHS, union):

        support = self.itemset_supports
        confidence = support[union] / support[LHS]
        return confidence


    # loops through each of the L_2...L_k tables generated by the algorithm. For each L,
    # it iterates through each itemset (row) and generates all possible association rules for the itemset.
    # It then calls get_confidence() to get the confidence of the rule. If the association rule is above threshold,
    # the association rule is saved.
    def generate_assocation_rules(self):

        cur = self.cur
        self.k = 2
        rules = [] #list of tuples, where tuple[0] = left hand side of rule and tuple[1] = right hand side


        while self.get_C_size() > 0:

            print(f'k={self.k}')
            cur.execute(f'select * from L{self.k}')
            rows = cur.fetchall()
            itemsets = []
            for row in rows:
                itemsets.append(row[2:])

            for itemset in itemsets:
                LHS = []
                for comb in itertools.combinations(itemset, self.k-1):
                    comb = set(comb)
                    LHS.append(comb)

                for l in LHS:
                    for r in itemset:
                        if r not in l:
                            confidence = self.get_confidence(frozenset(l), frozenset(itemset))
                            rule = (l, r)
                            print('Rule: ', rule)
                            if confidence > self.min_confidence:
                                print(f'Confidence of {confidence} above threshold. Adding rule...')
                                rules.append((rule, confidence, self.itemset_supports[frozenset(itemset)]))
                            else:
                                print(f'Confidence of {confidence} below threshold. Skipping rule...')

                            print('\n\n')

            self.k += 1

            print('\n\n')

        self.rules = rules
        for rule in rules:
            print(rule)


    # generates example-run.txt by printing each frequent itemset and association rule above threshold
    def create_output_file(self):

        text_file = open("example-run.txt", "w")

        print(f'\n\n==Frequent Itemsets (min_sup={self.min_support*100}%)\n\n')
        text_file.write(f'==Frequent Itemsets (min_sup={self.min_support*100}%)\n\n')

        # sort the dictionary of itemsets by their support in descending order and print them
        for itemset in sorted(self.itemset_supports, key=self.itemset_supports.get, reverse=True):
            itemset_str = '['
            if isinstance(itemset, frozenset):
                for item in itemset:
                    itemset_str += item + ', '
                itemset_str = itemset_str[:-2]
            else:
                itemset_str += itemset
            itemset_str += ']'
            print(itemset_str, round(self.itemset_supports[itemset]/self.num_rows, 2), '\n')
            text_file.write(f'{itemset_str}, {round(self.itemset_supports[itemset] / self.num_rows * 100, 2)}%\n\n')

        print('\n\n\n\n\n')
        text_file.write('\n\n')

        print(f'==High-confidence association rules (min_conf={self.min_confidence*100}%)\n\n')
        text_file.write(f'High-confidence association rules (min_conf={self.min_confidence*100}%)\n\n')

        # sort rules by their confidence in descending order
        self.rules.sort(key=operator.itemgetter(1), reverse=True)
        for rule, confidence, support in self.rules:
            lhs = rule[0]
            rhs = rule[1]
            rule_str = '['
            if isinstance(lhs, set):
                for item in lhs:
                    rule_str += item + ', '
                rule_str = rule_str[:-2]
            else:
                rule_str += lhs
            rule_str += '] ==> ['

            if isinstance(rhs, set):
                for item in rhs:
                    rule_str += item + ', '
                rule_str = rule_str[:-2]
            else:
                rule_str += rhs
            rule_str += ']'

            # print(f'{rule[0]} ==> {rule[1]} (\nConfidence {round(confidence * 100, 2)}%, Support {round(support / self.num_rows * 100, 2)}%)\n\n')
            print(f'{rule_str} (\nConfidence {round(confidence * 100, 2)}%, Support {round(support / self.num_rows * 100, 2)}%)\n\n')
            text_file.write(f'{rule_str} (\nConfidence {round(confidence * 100, 2)}%, Support {round(support / self.num_rows * 100, 2)}%)\n\n')

        text_file.close()











    # main loop of the algorithm. First calculates all frequent itemsets of size 1, then repeatedly
    # finds the support of each itemset in C_k, generates L_k from C_k, and generates C_k+1 from L_k. Continues
    # until C_K has no candidate itemsets to calculate the support for.
    def apriori(self):

        candidate_size = 1

        self.get_single_itemsets()

        while candidate_size > 0:

            self.update_candidate_supports()
            self.prune()
            self.get_candidates()
            candidate_size = self.get_C_size()

        print(f'C{self.k} has no more candidate itemsets. Calculating possible assocation rules...')
        self.generate_assocation_rules()
        self.create_output_file()



A = Apriori(min_supp=0.005, min_conf=0.38)
A.apriori()
