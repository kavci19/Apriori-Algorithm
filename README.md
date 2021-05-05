# Apriori-Algorithm

Name: Kaan Avci
UNI: koa2107

Name: Brian Yang
UNI: by2289



----List of all the files submitted:----

1. Apriori.py 	                (contains the code)
2. README.txt               	(description of steps, program structure, etc.)
3. example-run.txt           	(contains transcript of the test case for min_sup= 0.005 and min_conf = 0.38)
4. INTEGRATED-DATASET.csv       (contains the dataset for the association rule mining)
5. requirements.txt             (contains the requirements file with the packages needed to import)



----How to Run Program:----

1. Move to the Project3 directory in koa2107's directory

2. Install the necessary requirements via:
    pip3 install -r requirements.txt

3. Execute the command:
    python3 Apriori.py INTEGRATED-DATASET.csv 0.005 0.38



----Dataset and Cleaning----

I used the "Service Requests from 2010 to Present" dataset which can be found here:

    https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9

This dataset contains information regarding complaints made in New York, including location, complaint type, borough, etc. The complaints range 
from noise complaints, illegal parking, no hot/cold water, poor road condition, etc.

I downloaded the original CSV file and created the INTEGRATED-DATASET.csv file to only contain the first 15k rows of the dataset. The original 
dataset contains over 25M rows (!), so I had to trim the data to ensure that it uploaded to gradescope in a reasonable amount of time. Since the 
dataset is sorted by date of the incidents, the first 15k rows correspond to complaints filed in the week from March 8, 2020 to March 16, 2020. 


INTEGRATED-DATASET.csv only contains specific columns from the original dataset: 'Complaint Type', 'Location Type', 'Street Name', 'Borough'. I 
found that this combination of attributes yielded the most interesting and meaningful rules. For example, 'Incident Zip', 'Borough', and 'City' 
together created many redundant or obvious association rules (such as Borough=Bronx -> City=Bronx) because much of the same information is 
repeated. The combination of 'Complaint Type', 'Location Type', 'Street Name', 'Borough' allowed the algorithm to mine compelling information. For 
example, some association rules found were regarding which boroughs are most likely to have certain types of complaints, the locations that 
specific types of complaints occur, and more. 

Thus, to create the csv file from scratch:
    1. use only the first 15k rows of the original dataset
    2. only keep the columns 'Complaint Type', 'Location Type', 'Street Name', 'Borough'

The above tasks can be accomplished via using a pandas Dataframe to read only the first 15,000 rows of the original CSV file, and to drop the 
columns that are not ['Complaint Type', 'Location Type', 'Street Name', 'Borough'].




----Design of Project----

The program is composed of two phases:
    1. Determine all frequent itemsets and their support values
    2. Generate all possible association rules from the frequent itemsets and only keep the ones above a certain confidence threshold

The program's main loop is contained in the function apriori(), which makes calls to many other helper functions during the algorithm. The purpose
of each helper function is commented in the code of Apriori.py.

The program follows the structure of the Apriori algorithm discussed in Section 2.1.1 of the Agrawal and Srikant paper in VLDB 1994. I used sqlite
to implement the creation and modification of the C and L tables tables using SQL.

First, the imported INTEGRATED-DATASET.csv is converted to a SQL table called Complaints. 
The C_k and L_k tables are also created online during the algorithm in sql.

To determine all frequent itemsets and their support values, the program:
    1. Generates all frequent itemsets of size 1 by iterating through each cell in the original Complaints table and making each unique cell its 
    own row in C_1 (candidate itemsets of size 1)
    
    2. Updates the support of each itemset in C_1 by iterating through each row in the original Complaints table and counting which itemsets 
    are a subset of each row in the Complaints table.

    3. Generates L_1 table with only the itemsets in C_1 above support

Then, the subsequent candidate tables C_k are generated via sql joins of L_{k-1} with itself via the following query pattern:

insert into C_k
select p.item1, p.item2, ... p.item{k-1}, q.item{k-1}
from L_{k-1} p, L_{k-1} q
where p.item1 = q.item1, ..., p.item{k-2} = q.item{k-2}, p.item{k-1} < q.item{k-1}

The SQL statements for the generation of these tables is automatically created via the helper functions get_sql_candidate_table_statement(self) and
 get_sql_create_table_statement(self, type).

This process of generating C_k from self joining L_{k-1}, finding the support of each itemset in C_k, and creating L_k from the frequent itemsets
in C_K is repeated until C_k has no more frequent itemsets.

As these C and L tables are generated, the support of each itemset is remembered in a dictionary that maps an itemset to its support value. This
dictionary is used in the next step.

To determine the above-threshold association rules, the program:
    1. Iterates through each itemset (row) in L_2, L_3, ..., L_k. From each itemset (row), the program generates all possible association rules. 
    The confidence for a rule is calculated by looking up the support of the union of the LHS and RHS and dividing by the support of the LHS 
    (itemset supports are found in the dictionary created earlier). If the rule is above confidence and support threshold, it is saved and 
    later printed to the output text file.





----Compelling Sample Run----

The sample run uses minimum support of 0.005 and minimum confidence of 0.38:
    python3 Apriori.py INTEGRATED-DATASET.csv 0.005 0.38

Here are some of the insightful association rules:

1. 
[Location Type = Residential Building/House, Borough = BRONX] ==> [Complaint Type = Noise - Residential] 
(Confidence 98.51%, Support 3.97%)

Here we see that over 98% of the complaints that are in residential areas in the Bronx are about noise complaints. This rule is supported by 3.97% 
= 596 complaint records. This is interesting to note that this one complaint took such a huge majority of complaints. Other complaints, such as 
rodent complaints, illegal parking, blocked driveway, homeless person assistance, etc had nowhere near the representation that noise complaints 
have in Bronx, NY.


2. 
[Complaint Type = Abandoned Vehicle] ==> [Borough = QUEENS] 
(Confidence 47.13%, Support 0.82%)

47% of complaints about abandoned vehicles were in Queens! Considering there is Brooklyn, Manhattan, Bronx, Staten Island, and other locations, it
 is interesting to note that almost have of the complaints about abandoned vehicles are in Queens. This could lead a data analyst to question: why
  are there so many complaints about abandoned vehicles are in Queens? Is it because Queens is the largest borough in New York, or are there other
   underlying factors?


3.
[Complaint Type = General Construction/Plumbing] ==> [Borough = BROOKLYN] 
(Confidence 42.79%, Support 1.82%)

It is interesting to note that almost 43% of constructing/plumbing complaints come from Brooklyn. This could possibly lead an analyst to 
investigate if there is perhaps more noise-related complaints in regards to construction in Brooklyn moreso than any other borough.


4. 
[Complaint Type = Noise] ==> [Borough = MANHATTAN] 
(Confidence 38.12%, Support 0.51%)

Why are so many noise complaints from Manhattan? Perhaps its because Manhattan may be one of the most densely populated boroughs. Areas like 
Chinatown are extremely dense in population, so complaints about noise may be more likely.


5. 
[Location Type = Club/Bar/Restaurant] ==> [Complaint Type = Noise - Commercial] 
(Confidence 98.04%, Support 1.0%)

Although this isn't too surprising, it's interesting to note that 98% of complaints about clubs/bars/restaurants are noise related.

