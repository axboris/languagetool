# -*- coding: iso-8859-1 -*-
# A probabilistic part-of-speech tagger (see the QTag paper) with
# a rule-based extension.
# (c) 2003 Daniel Naber <daniel.naber@t-online.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import os
import re
import string
import sys
import cPickle
import htmlentitydefs

class Tagger:
	"""POS-tag any text. The result in XML can be used to re-build the original
	text by concatenating all contents of the <w> tags. Whitespace characters 
	have term=None and type=None, i.e. they are inside their own <w>
	elements. Words that could not be tagged have type=unknown."""

	db_word_name = os.path.join("data", "words")
	db_seq_name1 = os.path.join("data", "seqs1")
	db_seq_name2 = os.path.join("data", "seqs2")
	#uncountable_name = os.path.join("data", "uncountable.txt")
	
	def __init__(self, db_word_name=None, db_seq_name=None):
		"""Initialize the tagger, optionally using the given
		file names that will be used to load and save data later."""
		self.data_table = None
		self.seqs_table_followed_by = None	# tag sequences: table[tag1,tag2] = value
		self.seqs_table_follows = None		# tag sequences: table[tag1,tag2] = value
		if db_word_name:
			self.db_word_name = db_word_name
		if db_seq_name:
			self.db_seq_name = db_seq_name
		#if db_seq_name:	#fixme
		#	self.db_seq_name = db_seq_name
		#uncountable_nouns = self.loadUncountables()
		self.word_count = 0
		return

	def loadUncountables(self):
		"""TODO: not used yet."""
		l = []
		f = open(self.uncountable_name)
		while 1:
			line = f.readline()
			if not line:
				break
			line = line.strip()
			if not line.startswith("#") and line != '':
				l.append(line)
		f.close()
		return l
		
	def bindData(self):
		"""Load the word/POS tag and POS tag sequence data from disk."""
		try:
			self.data_table = cPickle.load(open(self.db_word_name))
		except IOError:
			print >> sys.stderr, "No date file '%s' yet, starting with empty table." % self.db_word_name
			self.data_table = {}
		try:
			self.seqs_table_followed_by = cPickle.load(open(self.db_seq_name1))
		except IOError:
			print >> sys.stderr, "No date file '%s' yet, starting with empty table." % self.db_seq_name1
			self.seqs_table_followed_by = {}
		try:
			self.seqs_table_follows = cPickle.load(open(self.db_seq_name2))
		except IOError:
			print >> sys.stderr, "No date file '%s' yet, starting with empty table." % self.db_seq_name2
			self.seqs_table_follows = {}
		return

	def commitData(self):
		"""Save the word/POS tag and POS tag sequence data to disk."""
		print >> sys.stderr, "Words = %d" % self.word_count
		print >> sys.stderr, "Known words = %d" % len(self.data_table.keys())
		print >> sys.stderr, "Known sequences = %d" % len(self.seqs_table_followed_by.keys())
		print >> sys.stderr, "Commiting results..."
		cPickle.dump(self.data_table, open(self.db_word_name, 'w'), 1)
		cPickle.dump(self.seqs_table_followed_by, open(self.db_seq_name1, 'w'), 1)
		cPickle.dump(self.seqs_table_follows, open(self.db_seq_name2, 'w'), 1)
		return
	
	def deleteData(self):
		"""Remove the word/POS tag and POS tag sequence data files from disk."""
		print >> sys.stderr, "Deleting old data files..."
		try:
			os.remove(self.db_word_name)
		except OSError, e:
			print >> sys.stderr, "Note: Could not delete file: %s" % e
		try:
			os.remove(self.db_seq_name1)
		except OSError, e:
			print >> sys.stderr, "Note: Could not delete file: %s" % e
		try:
			os.remove(self.db_seq_name2)
		except OSError, e:
			print >> sys.stderr, "Note: Could not delete file: %s" % e
		return

	def buildData(self, filenames):
		"""Load BNC files in XML or SGML format and count the word/POS
		occurences and the POS tag sequences."""
		tagged_words = []
		for filename in filenames:
			print >> sys.stderr, "Loading %s..." % filename
			text = PreTaggedText(filename)
			tagged_words.extend(text.getTaggedWords())
		#print tagged_words
		self.word_count = self.word_count + len(tagged_words)
		text.addToData(tagged_words, self.data_table, self.seqs_table_followed_by, self.seqs_table_follows)
		return

	def buildDataFromString(self, s):
		"""Take a string with format "word1/tag1 word2/tag2 ..." and
		count the word/POS occurences and the POS tag sequences.
		Only useful for the test cases."""
		pairs = re.compile("\s+").split(s)
		tagged_words = []
		split_regex = re.compile("/")
		for pair in pairs:
			pair = split_regex.split(pair)
			if len(pair) != 2:
				# e.g. punctuation
				continue
			word = pair[0]
			tag = pair[1]
			tagged_words.append((word, tag))
		text = TextToTag()
		text.addToData(tagged_words, self.data_table, self.seqs_table_followed_by, self.seqs_table_follows)
		return

	def tagFile(self, filename):
		"""POS-tag the contents of a text file and return XML that contains
		the original text with each word's POS tag in the "type"
		attribute."""
		text = TextToTag()
		text.setFilename(filename)
		tagged_words = text.tag(self.data_table, self.seqs_table_followed_by, self.seqs_table_follows)
		#print tagged_words
		xml = text.toXML(tagged_words)
		return xml

	def tagText(self, strng):
		"""POS-tag a string and return a list of (word, normalized word, tag)
		triples."""
		text = TextToTag()
		text.setText(strng)
		tagged_words = text.tag(self.data_table, self.seqs_table_followed_by, self.seqs_table_follows)
		return tagged_words

	def tagTexttoXML(self, strng):
		"""POS-tag a string and return a list of (word, normalized word, tag)
		triples."""
		text = TextToTag()
		text.setText(strng)
		tagged_words = text.tag(self.data_table, self.seqs_table_followed_by, self.seqs_table_follows)
		xml = text.toXML(tagged_words)
		return xml

	def tagSeq(self, triple):
		"""Return the probability of a 3-POS-tag sequence."""
		# FIXME
		if len(triple) != 3:
			#TODO?: throw exception
			print >> sys.stderr, "Sequence does not consist of 3 tokens: '%s'" % str(seq)
			return None
		try:
			probability = self.seqs_table[triple]
		except KeyError:
			probability = 0
		return probability

	def tagWord(self, word):
		"""See Text.tagWord()"""
		text = TextToTag()
		text.setText("")
		tag = text.tagWord(word, self.data_table)
		return tag

	def guessTagTest(self, word):
		"""See Text.guessTags(). For test cases only."""
		text = TextToTag()
		text.setText("")
		tag = text.guessTags(word)
		return tag

class Text:

	DUMMY = None
	number_regex = re.compile("^[0-9.,/\-]+$")
	time_regex = re.compile("\d(am|pm)$")
	bnc_regex = re.compile("<(w|c) (.*?)>(.*?)<", re.DOTALL)

	mapping_file = os.path.join("data", "c7toc5.txt")

	def __init__(self):
		self.count_unambiguous = 0
		self.count_ambiguous = 0
		self.count_unknown = 0
		self.whitespace = re.compile("\s+$")
		self.nonword = re.compile("([\s,:;]+)")
		self.nonword_punct = re.compile("([,:;]+)")
		self.sentence_end = re.compile("([.!?]+)$")
		self.bnc_word_regexp = re.compile("<W\s+TYPE=\"(.*?)\".*?>(.*?)</W>", \
			re.DOTALL|re.IGNORECASE)
		self.mapping = self.loadMapping()
		return
		
	def loadMapping(self):
		f = open(self.mapping_file)
		line_count = 1
		mapping = {}
		while 1:
			line = f.readline().strip()
			if not line:
				break
			l = re.split("\s+", line)
			if not len(l) == 2:
				print >> sys.stderr, "No valid mapping in line %d: '%s'" % (line_count, line)
			(c7, c5) = l[0], l[1]
			if mapping.has_key(c7):
				print >> sys.stderr, "No valid mapping in line %d: '%s', duplicate key '%s'" % (line_count, line, c7)
				continue
			mapping[c7] = c5
			#print "%s -> %s" % (c7, c5)
			line_count = line_count + 1
		f.close()
		return mapping
		
	def expandEntities(self, text):
		"""Take a text and expand a few selected entities. Return the same
		text with entities expanded. (We cannot simply parse the file with 
		DOM, as we don't have an XML DTD -- the original files were SGML.)"""
		### TODO: use Entities module
		text = re.compile("&amp;", re.IGNORECASE).sub("&", text)
		# TODO: several entities are missing here:
		#text = re.compile("&#(x..);", re.IGNORECASE).sub(self.expandHexEntities, text)
		text = re.compile("&#xA3;", re.IGNORECASE).sub("�", text)
		return text

	#def expandHexEntities(self, matchobj):
	#	htmlentitydefs.entitydefs[]
	#	s = u'\%s' % matchobj.group(1)
	#	#s = "Y"
	#	return s

	def getBNCTuples(self, text):
		"""Return a list of (tag, word) tuples from text if
		text is a BNC Sampler text in XML or SGML format. Otherwise
		return an empty list. The tags are mapped from the C7 tag set
		to the much smaller C5 tag set."""
		l = []
		pos = 0
		while 1:
			m = self.bnc_regex.search(text, pos)
			if not m:	
				break
			tag = m.group(2)
			if self.mapping.has_key(tag):
				tag = self.mapping[tag]
			else:
				#print "no mapping: %s" % tag
				pass
			if m.group(3):
				l.append((tag, m.group(3).strip()))
				#print "- %s/%s" % (tag, m.group(3).strip())
			pos = m.start()+1
		return l
		
	def normalise(self, text):
		"""Take a string and remove XML markup and whitespace at the beginning 
		and the end. Return the modified string."""
		# sometimes there's <PB...>...</PB> *inside* <W...>...</W>!
		text = re.compile("<.*?>", re.DOTALL|re.IGNORECASE).sub("", text)
		text = text.strip()
		return text

	def splitBNCTag(self, tag):
		"""Take a string with BNC tags like 'NN1-NP0' and return a list,
		e.g. ['NN1', 'NP0']. For single tags like 'NN0' this will
		be returned: ['NN0']."""
		tags = re.split("-", tag)
		return tags

	def guessTags(self, word):
		"""Take a word and guess which POS tags it might have and return
		those POS tags. This considers e.g. word prefixes, suffixes and 
		capitalization. If no guess can be made, None is returned."""
		# TODO: really return more than one tag

		# �25 etc:
		if word.startswith(u"�") or word.startswith(u"$"):
			return 'NN0'

		# numbers:
		if self.number_regex.match(word):
			return 'CRD'
			
		# e.g. HIV
		if len(word) >= 2 and word == word.upper():
			return 'NN0'

		# this >=3 limit also prevents to assign 'A' (i.e. determiner
		# at sentence start) NP0, of course that's only relevant
		# for the test cases:
		if len(word) >= 3 and word[0] in string.uppercase:	# e.g. "Jefferson"
			return 'NP0'

		# e.g. freedom, contentment, celebration, assistance, fighter,
		# violinist, capacity
		noun = ['dom', 'ment', 'tion', 'sion', 'ance', 'ence', 'er', 'or', 
			'ist', 'ness', 'icity']
		for suffix in noun:
			if word.endswith(suffix):
				return 'NN1'

		# e.g. quickly
		if word.endswith("ly"):
			return 'AV0'

		# e.g. 8.55am
		if self.time_regex.search(word):
			return 'AV0'

		# e.g. extensive, heroic, financial, portable, hairy
		# mysterious, hopeful, powerless
		# 'en' was left out, could also be a verb
		adj = ['ive', 'ic', 'al', 'able', 'y', 'ous', 'ful', 'less']
		for suffix in adj:
			if word.endswith(suffix):
				return 'AJ0'

		# e.g. publicize, publicise, activate, simplify
		# 'en' was left out, could also be a adjective
		verb = ['ize', 'ise', 'ate', 'fy']
		for suffix in verb:
			if word.endswith(suffix):
				# fixme: could also be VVB
				return 'VVI'

		return None
	
	def tagWord(self, word, data_table):
		"""Find all possible tags for a word and return a list of tuples:
		[(orig_word, normalised_word, [(tag, probability])]"""
		orig_word = word
		word = self.normalise(word)
		#word = re.compile("[^\w' ]", re.IGNORECASE).sub("", word)
		
		#if word and self.nonword_punct.match(word):
		#	# punctuation
		#	return [(orig_word, orig_word, [])]
		if (not word) or self.whitespace.match(word):
			# word is just white space
			return [(orig_word, None, [])]
		
		# sanity check:
		if word.count("'") > 1:
			print >> sys.stderr, "*** What's this, more than one apostroph: '%s'?" % word

		# Special cases: BNC tags "wasn't" like this: "<w VBD>was<w XX0>n't"
		# Call yourself, but don't indefinitely recurse.
		special_cases = ("n't", "'s", "'re", "'ll", "'ve")
		for special_case in special_cases:
			special_case_pos = word.find(special_case)
			if special_case_pos != -1 and special_case_pos != 0:
				first_part = self.tagWord(word[0:special_case_pos], data_table)[0]
				second_part = self.tagWord(special_case, data_table)[0]
				tag_results = []
				#TODO: return probability?:
				#print second_part
				tag_results.append((word[0:special_case_pos], first_part[1], first_part[2]))
				tag_results.append((special_case, second_part[1], second_part[2]))
				return tag_results

		# TODO?: ignore upper/lower case?, no -- seems to decrease precision
		#word = word.lower()
		#if not data_table.has_key(word):
		#	word = word.lower()
		#	#if data_table.has_key(word):
		#	#	print "lower: %s" % word
		#if not data_table.has_key(word) and len(word) >= 1:
		#	word = "%s%s" % (word[0].upper(), word[1:])
		#	#if data_table.has_key(word):
		#	#	print "upper: %s" % word

		if not data_table.has_key(word):
			# word is unknown
			#print "unknown: '%s'" % word
			self.count_unknown = self.count_unknown + 1
			guess_tag = self.guessTags(word)
			if guess_tag:
				return [(orig_word, word, [(guess_tag, 1)])]
			else:
				return [(orig_word, word, [("unknown", 1)])]
		else:
			pos_table = data_table[word].table
			if len(pos_table) == 1:
				# word is unambiguous
				self.count_unambiguous = self.count_unambiguous + 1
				return [(orig_word, word, [(pos_table.keys()[0], 1)])]
			else:
				# word is ambiguous
				tag_tuples = []
				for pos_tag in pos_table.keys():
					#print "pos_tag=%s -> %.2f" % (pos_tag, pos_table[pos_tag])
					tag_tuples.append((pos_tag, pos_table[pos_tag]))
				self.count_ambiguous = self.count_ambiguous + 1
				return [(orig_word, word, tag_tuples)]

	def addToData(self, tagged_words, data_table, seqs_table_followed_by, seqs_table_follows):
		"""Count words and POS tags so they can later be added
		to the persistent storage."""
		tag_list = self.addWords(tagged_words, data_table)
		self.addTagSequences(tag_list, seqs_table_followed_by, seqs_table_follows)
		return
	
	def addWords(self, tagged_words, data_table):
		"""For each word, save the tag frequency to data_table so
		it can later be added to the persistent storage. Return
		a list of all tags."""
		all_tags_list = []
		for (word, tag) in tagged_words:
			#only for testing if case-insensitivity is better:
			#word = word.lower()
			all_tags_list.append(tag)
			tag_list = self.splitBNCTag(tag)
			assert(len(tag_list) == 1 or len(tag_list) == 2)
			#print "word/pos_list: %s/%s" % (word, tag_list)
			if data_table.has_key(word):
				# word is already known
				word_table = data_table[word].table
				for tag in tag_list:
					if word_table.has_key(tag):
						word_table[tag] = word_table[tag] + 1.0/len(tag_list)
						#print "word_table[%s] += %f" % (tag, 1.0/len(tag_list))
					else:
						word_table[tag] = 1.0/len(tag_list)
						#print "word_table[%s] = %f" % (tag, word_table[tag])
			else:
				word_table = {}
				for tag in tag_list:
					word_table[tag] = 1.0/len(tag_list)
					#print "word_table[%s] = %f" % (tag, word_table[tag])
				data_table[word] = WordData(word, word_table)
		# Normalize data_table values so they are probabilities (0 to 1):
		for e in data_table.keys():
			t = data_table[e].table
			occ_all = 0
			for occ in t.values():
				occ_all = occ_all + occ
			for key in t.keys():
				t[key] = t[key] / occ_all
		# debug:
		#for e in data_table.keys():
		#	print "%s, %s" % (e, data_table[e])
		return all_tags_list
		
	def addTagSequences(self, tag_list, seqs_table_followed_by, seqs_table_follows):
		"""Save information about POS tag tuples to seqs_table."""
		# TODO: add dummy entries
		if len(tag_list) == 0:
			return
		i = 0

		### FIXME: does this work if data is added later? probably not...:
		count_followed_by = {}
		count_follows = {}
		
		while 1:
			if i >= len(tag_list)-1:
				break
			tag0 = tag_list[i]
			key = ()
			if self.mapping.has_key(tag0):
				tag0 = self.mapping[tag0]
			tag1 = tag_list[i+1]
			if self.mapping.has_key(tag1):
				tag1 = self.mapping[tag1]
			try:
				seqs_table_followed_by[(tag0,tag1)] = seqs_table_followed_by[(tag0,tag1)] + 1
			except KeyError:
				seqs_table_followed_by[(tag0,tag1)] = 1
			try:
				count_followed_by[tag0] = count_followed_by[tag0] + seqs_table_followed_by[(tag0,tag1)]
			except KeyError:
				count_followed_by[tag0] = seqs_table_followed_by[(tag0,tag1)]

			try:
				seqs_table_follows[(tag0,tag1)] = seqs_table_follows[(tag0,tag1)] + 1
			except KeyError:
				seqs_table_follows[(tag0,tag1)] = 1
			try:
				count_follows[tag0] = count_follows[tag0] + seqs_table_follows[(tag0,tag1)]
			except KeyError:
				count_follows[tag0] = seqs_table_follows[(tag0,tag1)]
			i = i + 1

		#debug:
		#print "FOLLOWED BY:"
		#for k in seqs_table_followed_by.keys():
		#	print "%s -> %s" % (k, seqs_table_followed_by[k])
		#print "FOLLOWS:"
		#for k in seqs_table_follows.keys():
		#	print "%s -> %s" % (k, seqs_table_follows[k])

		# Normalize to 0-1 range:
		# TODO: do these numbers become too small, as the Qtag paper states?		
		for t in seqs_table_followed_by.keys():
			#print "#%s'" % t[0]
			seqs_table_followed_by[t] = float(seqs_table_followed_by[t]) / float(count_followed_by[t[0]])
		for t in seqs_table_follows.keys():
			seqs_table_follows[t] = float(seqs_table_follows[t]) / float(count_follows[t[0]])

		#debug:
		#print "FOLLOWED BY (norm):"
		#for k in seqs_table_followed_by.keys():
		#	print "%s -> %s" % (k, seqs_table_followed_by[k])
		#print "FOLLOWS (norm):"
		#for k in seqs_table_follows.keys():
		#	print "%s -> %s" % (k, seqs_table_follows[k])
		return


class TextToTag(Text):
	"""Any text (also pre-tagged texts from the BNC -- for 
	testing the tagger)."""

	DUMMY = None
	
	def __init__(self):
		self.text = None
		Text.__init__(self)
		return

	def setText(self, text):
		self.text = text
		return

	def setFilename(self, filename):
		f = open(filename)
		self.text = f.read()
		f.close()
		return
	
	def getPrevToken(self, i, tagged_list):
		"""Find the token previous to the token at position i from tagged_list,
		ignoring whitespace tokens. Return a tuple (word, tuple_list),
		whereas tuple_list is a list of (tag, tag_probability) tuples."""
		j = i-1
		while j >= 0:
			(orig_word_tmp, tagged_word_tmp, tag_tuples_tmp) = self.getTuple(tagged_list[j])
			j = j - 1
			if not tagged_word_tmp:
				continue
			else:
				prev = tag_tuples_tmp
				return (orig_word_tmp, prev)
		return (None, None)

	def getNextToken(self, i, tagged_list):
		"""Find the token next to the token at position i from tagged_list,
		ignoring whitespace tokens. See self.getPrevToken()"""
		j = i + 1
		while j < len(tagged_list):
			(orig_word_tmp, tagged_word_tmp, tag_tuples_tmp) = self.getTuple(tagged_list[j])
			j = j + 1
			if not tagged_word_tmp:
				continue
			else:
				next = tag_tuples_tmp
				return (orig_word_tmp, next)
		return (None, None)

	def getBestTagSimple(self, prev, tag_tuples, next, seqs_table, i, tag_table):
		"""Return the most probable tag without taking context into
		account. Only useful for testing and checking the baseline."""
		max_prob = 0
		best_tag = None
		for tag_tuples_here in tag_tuples:
			prob = tag_tuples_here[1]
			if prob >= max_prob:
				max_prob = prob
				best_tag = tag_tuples_here[0]
		return best_tag

	def getBestTag(self, prev, tag_tuples, next, seqs_table, i, tag_table):
		"""Check the probability of all 3-tag sequences and choose that with
		the highest combined probability."""
		max_prob = 0
		max_prob_no_context = 0		# special case, mostly for test cases
		best_tag = None
		for tag_tuples_prev in prev:
			for tag_tuples_here in tag_tuples:
				#print tag_tuples_here
				for tag_tuples_next in next:
					seq = (tag_tuples_prev[0], tag_tuples_here[0], tag_tuples_next[0])
					seq_prob = 0	# sequence probability
					try:
						seq_prob = seqs_table[seq]
					except KeyError:
						pass
					prob_combined = seq_prob * tag_tuples_here[1]
					#print "prob_combined = %s * %s" % (seq_prob, tag_tuples_here[1])
					k = (i, tag_tuples_here[0])
					try:
						tag_table[k] = tag_table[k] + prob_combined
					except KeyError:
						tag_table[k] = prob_combined
					# also work if all contexts have probability == 0,
					# use the pos tag probability without context then:
					if tag_tuples_here[1] >= max_prob_no_context:
						max_prob_no_context = tag_tuples_here[1]
						best_tag_no_context = tag_tuples_here[0]
					if prob_combined >= max_prob:
						max_prob = prob_combined
						best_tag = tag_tuples_here[0]
					#print "##seq=%s, %.7f*%.2f=%f" % (str(seq), seq_prob, tag_tuples_here[1], prob_combined)
		if max_prob == 0:
			best_tag = best_tag_no_context
		return best_tag

	def checkBNCMatch(self, i, tagged_list_bnc, word, best_tag, data_table):
		"""Check for mismatches, i.e. POS tags that differ from the original
		tag in BNC. Print out a warning for all those differences and return
		1, otherwise return 0. Note that the BNC's tags are only correct 
		in 97-98%. If the original tag is 'UNC' and this tagger's tag is
		not 'unknown', this is still considered a mismatch."""
		if i >= len(tagged_list_bnc)-1:
			print >> sys.stderr, "Index out of range..."
			return 0
		if not tagged_list_bnc[i]:
			return 0
		word_from_bnc, tags_from_bnc = tagged_list_bnc[i]
		#print "%s ?= %s" % (word_from_bnc, word)
		if best_tag == 'unknown':
			# 'UNC' means unclassified in BNC, assume that this corresponds
			# to out 'unknown':
			best_tag = 'UNC'
		guessed = 1
		# fixme: remove, debugging only:
		if data_table.has_key(word):
			guessed = 0
		if not word == word_from_bnc:
			print >> sys.stderr, "*** word mismatch: '%s'/'%s'" % (word, word_from_bnc)
			#sys.exit()
		elif not (best_tag in tags_from_bnc) and \
				tags_from_bnc[0][0] != 'Y':		# ignore punctuation tags
			print >> sys.stderr, "*** tag mismatch (guessed=%d): got %s/%s, expected %s/%s" % \
				(guessed, word, best_tag, word_from_bnc, tags_from_bnc)
			return 1
		return 0

	def getStats(self, count_wrong_tags):
		"""Get some human-readable statistics about tagging success,
		e.g. number and percentage of correctly tagged tokens."""
		res = "<!-- Statistics:\n"
		sum = self.count_unknown + self.count_unambiguous + self.count_ambiguous
		if sum > 0:
			res = res + "count_unknown = %d (%.2f%%)\n" % (self.count_unknown, float(self.count_unknown)/float(sum)*100)
			#res = res + "count_unambiguous = %d (%.2f%%)\n" % (self.count_unambiguous, float(self.count_unambiguous)/float(sum)*100)
			res = res + "count_ambiguous = %d (%.2f%%)\n" % (self.count_ambiguous, float(self.count_ambiguous)/float(sum)*100)
			#res = res + "sum = %d\n" % sum
			if not count_wrong_tags == "n/a":
				res = res + "correct tags = %d (%.2f%%)\n" % (sum-count_wrong_tags, float(sum-count_wrong_tags)/float(sum)*100)
				#res = res + "count_wrong_tags = %d (%.2f%%)\n" % (count_wrong_tags, float(count_wrong_tags)/float(sum)*100)
		res = res + "-->"
		return res

	def applyConstraints(self, prev_word, curr_word, next_word, tagged_tuples):
		"""Some hard-coded and manually written rules that prevent mistaggings by 
		the probabilistic tagger. Removes incorrect POS tags from tagged_tuples.
		Returns nothing, as it works directly on tagged_tuples."""
		# demo rule just for the test cases:
		if curr_word and curr_word.lower() == 'demodemo':
			self.constrain(tagged_tuples, 'AA')
		# ...
		return

	def constrain(self, tagged_tuples, pos_tag):
		"""Remove the pos_tag reading from tagged_tuples. Returns nothing,
		works directly on tagged_tuples."""
		i = 0
		for t in tagged_tuples:
			if t[0] == pos_tag:
				del tagged_tuples[i]
			i = i + 1
		return
	
	def applyTagRules(self, curr_word, tagged_word, curr_tag):
		"""Some hard-coded and manually written rules that extent the
		tagging. Returns a (word, normalized_word, tag) triple."""
		# ...
		return None

	def tag(self, data_table, seqs_table_followed_by, seqs_table_follows):
		"""Tag self.text and return list of tuples
		(word, normalized word, most probable tag)"""
		self.text = self.expandEntities(self.text)
		is_bnc = 0
		word_matches = self.getBNCTuples(self.text)
		if len(word_matches) > 0:
			# seems like this is a BNC text used for testing
			is_bnc = 1
			print >> sys.stderr, "BNC text detected."
		else:
			word_matches = self.nonword.split(self.text)
			
		# Put sentence end periods etc into an extra element.
		# We cannot just split on periods etc. because that would
		# break inner-sentence tokens like "... No. 5 ...":
		# fixme: only work on the last element (not counting white space)
		# FIXME: doesn't work here: "I cannot , she said."
		if not is_bnc:
			j = len(word_matches)-1
			while j >= 0:
				w = word_matches[j]
				s_end_match = self.sentence_end.search(w)
				if s_end_match:
					word_matches[j] = w[:len(w)-len(s_end_match.group(1))]
					word_matches.insert(j+1, s_end_match.group(1))
					break
				j = j - 1
			
		#print "word_matches=%s" % word_matches
		i = 0
		tagged_list = [self.DUMMY, self.DUMMY]
		tagged_list_bnc = [self.DUMMY, self.DUMMY]

		while i < len(word_matches):
			next_token = None
			tags = None
			if is_bnc:
				# word_matches[i] is a (tag,word) tuple
				(tag, word) = word_matches[i]
				if i+1 < len(word_matches):
					(next_token, foo) = word_matches[i+1]
				word = self.normalise(word)
				tags = self.splitBNCTag(tag)
			else:
				word = word_matches[i]
				if i+1 < len(word_matches):
					next_token = word_matches[i+1]
			if i + 2 < len(word_matches):
				# BNC special case: "of course" and some others are tagged as one word!
				tuple_word = "%s %s" % (word, word_matches[i+2])		# +2 = jump over whitespace
				if data_table.has_key(tuple_word):
					#print >> sys.stderr, "*** SPECIAL CASE %d '%s' ..." % (i, tuple_word)
					word = tuple_word
					i = i + 2
			r = Text.tagWord(self, word, data_table)
			#print r
			tagged_list.extend(r)

			if is_bnc:
				for el in r:
					# happens e.g. with this (wrong?) markup in BNC:
					#<W TYPE="CRD" TEIFORM="w">4's</W>
					# My tagger tags <4> and <'s>, so there's an offset
					# which makes futher comparisons BNC <-> tagger impossible,
					# so use this pseudo-workaround and just re-use the tags
					# for the <'s>, too:
					#print "%s -> %s" % (el[0], tags)
					tagged_list_bnc.append((el[0], tags))
			i = i + 1
		
		tagged_list.append(self.DUMMY)
		tagged_list.append(self.DUMMY)

		result_tuple_list = self.selectTagsByContext(tagged_list, seqs_table_followed_by, \
			seqs_table_follows, tagged_list_bnc, is_bnc, data_table)

		i = 0
		for tag_triple in result_tuple_list:
			triple = self.applyTagRules(tag_triple[0], tag_triple[1], tag_triple[2])
			if triple:
				result_tuple_list[i] = triple
			if self.sentence_end.search(tag_triple[0]):
				# make sure punctuation doesn't have tags:
				result_tuple_list[i] = (tag_triple[0], None, None)
			i = i + 1
		
		return result_tuple_list

	def selectTagsByContext(self, tagged_list, seqs_table_followed_by, \
		seqs_table_follows, tagged_list_bnc, is_bnc, data_table):
		
		count_wrong_tags = 0
		tag_probs = {}
		i = 0
		for tagged_triple in tagged_list:
			if tagged_triple != None and tagged_triple[1] == None:
				# ignore whitespace
				i = i + 1
				continue
			try:
				one = tagged_list[i]
				two = tagged_list[i+1]
				whitespace_jump = 0
				if two and two[1] == None:
					two = tagged_list[i+2]
					whitespace_jump = whitespace_jump + 1
				two_pos = i + 1 + whitespace_jump
				three = tagged_list[i+2+whitespace_jump]
				if three and three[1] == None:
					three = tagged_list[i+3+whitespace_jump]
					whitespace_jump = whitespace_jump + 1
				three_pos = i + 2 + whitespace_jump
			except IndexError:
				# list end
				break

			one_tags = [None]
			if one: one_tags = one[2]
			two_tags = [None]
			if two: two_tags = two[2]
			three_tags = [None]
			if three: three_tags = three[2]

			for one_tag in one_tags:
				tag_one_prob = 0
				if one_tag:
					tag_one_prob = one_tag[1]

				for two_tag in two_tags:
					tag_two_prob = 0
					if two_tag:
						tag_two_prob = two_tag[1]

					for three_tag in three_tags:
						tag_three_prob = 0
						if three_tag:
							tag_three_prob = three_tag[1]

						#print "** %s/%s/%s" % (one_tag, two_tag, three_tag)
						one_tag_prob = None
						if one_tag: one_tag_prob = one_tag[0]
						two_tag_prob = None
						if two_tag: two_tag_prob = two_tag[0]
						three_tag_prob = None
						if three_tag: three_tag_prob = three_tag[0]

						# FIXME?!:
						seq1 = (one_tag_prob, two_tag_prob)
						seq2 = (two_tag_prob, three_tag_prob)
						seq_prob = 0
						
						if one:
							try:
								seq_prob = seqs_table_followed_by[(one_tag_prob, two_tag_prob)] * \
									seqs_table_followed_by[(two_tag_prob, three_tag_prob)]
							except KeyError:
								pass
							prob_combined = seq_prob * tag_one_prob
							k1 = (i, one_tag[0])
							try:
								tag_probs[k1] = tag_probs[k1] + prob_combined
							except KeyError:
								tag_probs[k1] = prob_combined
						if two:
							try:
								seq_prob = seqs_table_follows[(one_tag_prob, two_tag_prob)] * \
									seqs_table_followed_by[(two_tag_prob, three_tag_prob)]
							except KeyError:
								pass
							prob_combined = seq_prob * tag_two_prob
							k2 = (two_pos, two_tag[0])
							try:
								tag_probs[k2] = tag_probs[k2] + prob_combined
							except KeyError:
								tag_probs[k2] = prob_combined
						if three:
							#FIXME: is this used at all???
							try:
								seq_prob = seqs_table_follows[(one_tag_prob, two_tag_prob)] * \
									seqs_table_follows[(two_tag_prob, three_tag_prob)]
							except KeyError:
								pass
							prob_combined = seq_prob * tag_three_prob
							k3 = (three_pos, three_tag[0])
							try:
								tag_probs[k3] = tag_probs[k3] + prob_combined
							except KeyError:
								tag_probs[k3] = prob_combined
						
			orig_word = None
			norm_word = None
			# the word that falls out of the window is assigned its final tag:
			if one:
				orig_word = one[0]
				norm_word = one[1]
				keys = tag_probs.keys()
				keys.sort()
				max_prob = 0
				best_tag = None
				for tag_prob in keys:
					if tag_prob[0] == i and tag_probs[tag_prob] >= max_prob:
						####print " K=%s, V=%s" % (tag_prob, tag_probs[tag_prob])
						max_prob = tag_probs[tag_prob]
						best_tag = tag_prob[1]
				tagged_list[i] = (orig_word, norm_word, best_tag)
				####print "BEST@%d: %s" % (i, best_tag)
			
			if is_bnc and one:
				orig_word = one[0]
				wrong_tags = self.checkBNCMatch(i, tagged_list_bnc, orig_word, best_tag, data_table)
				count_wrong_tags = count_wrong_tags + wrong_tags

			i = i + 1
			
		###
		stat = self.getStats(count_wrong_tags)
		print >> sys.stderr, stat

		# remove dummy entries:
		tagged_list.pop(0)
		tagged_list.pop(0)
		tagged_list.pop()
		tagged_list.pop()
		
		#print "<br>##tagged_list=%s<p>" % tagged_list
		return tagged_list

	def getTuple(self, tagged_list_elem):
		if not tagged_list_elem:
			orig_word = None
			tagged_word = None
			tag_tuples = None
		else:
			(orig_word, tagged_word, tag_tuples) = tagged_list_elem
		return (orig_word, tagged_word, tag_tuples)
	
	def toXML(self, tagged_words):
		"Show result as XML."
		xml_list = []
		for (orig_word, word, tag) in tagged_words:
			# fast appending:
			if not word and not tag:
				xml_list.append(' <w>%s</w>\n' % orig_word)
			else:
				xml_list.append(' <w term="%s" type="%s">%s</w>\n' % (word, tag, orig_word))
		xml = "<taggedWords>\n" + string.join(xml_list, "") + "</taggedWords>\n"
		return xml
	
	
class PreTaggedText(Text):
	"Text from the BNC Sampler in XML format."
	
	def __init__(self, filename):
		self.content = None
		Text.__init__(self)
		f = open(filename)
		self.content = f.read()
		f.close()
		return

	def getTaggedWords(self):
		"Returns list of tuples (word, tag)"
		text = self.expandEntities(self.content)
		word_matches = self.getBNCTuples(text)
		tagged_words = []
		for (tag, word) in word_matches:
			tagged_words.append((word, tag))
		return tagged_words


class WordData:
	"A term and the frequency of its tags."

	def __init__(self, word, table):
		self.word = word
		# table = tag / number of occurences
		# deep copy the hash table (TODO: use deep copy functions):
		self.table = {}
		for el in table:
			self.table[el] = table[el]
		return

	def __str__(self):
		"Show word data (debugging only!)"
		string = self.word + ":\n"
		for el in self.table:
			string = string + "\t" + el + ": " + str(self.table[el]) + "\n"
		return string
