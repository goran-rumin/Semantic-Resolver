import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def get_scores(sentence, documents):
    all_texts = list(documents)
    all_texts.insert(0, sentence)

    vectorizer = TfidfVectorizer(stop_words='english', decode_error="ignore")
    features = vectorizer.fit_transform(all_texts)
    scores = (features[0, :] * features[1:, :].T).A[0]
    return scores


def get_best_match(sentence, documents):
    scores = get_scores(sentence, documents)
    return documents[np.argmax(scores)]


def _test():
    my_phrases = [
        "John Nicholson (29 November 1790 – 13 April 1843) was popularly known as the Airedale Poet and also as the Bingley Byron. His most notable work was Airedale in Ancient Times. He died trying to cross the swollen River Aire near to Dixon's mill in Saltaire.",
        "Brigadier-General John Sanctuary Nicholson, CB, CMG, CBE, DSO (19 May 1863 – 21 February 1924) was a British soldier and politician. He was a Conservative Member of Parliament (MP) from 1921 to 1924. Born in Kensington, London, the son of William Nicholson and his wife Isabella. He was educated at Harrow and then in 1882 to the Royal Military College at Sandhurst. He was commissioned in 7th Hussars in February 1884 and in 1886 he spent eight years in India with his regiment before in 1894 being sent to Natal. The 7th Hussars joined a force at Mafeking to suppress a native rising in Matabeleland. During these operations he raised and commanded a Corps of British South Africa Police (BSAP). He became Commandant-General of the BSAP and Inspector-General of Volunteers in Rhodesia from 1898 until 1903. In 1903 he succeeded Baden-Powell as Inspector-General of South African Constabulary and retired from the post as a Colonel in 1907. With a father and brother both being members of parliament Nicholson contested a seat in East Dorset in the 1910 general election. He lost by 426 votes to Captain Guest but after a petition Guest was unseated. Nicholson stood again as a Conservative candidate in a by-election against Guests brother Henry Guest but was defeated again by a small margin. In the second general election of 1910 in December, he tried to get elected at Stafford but was defeated by 755 votes.",
        "John W. Nicholson (born c. 1934) is an American retired Brigadier General of the United States Army who was appointed secretary of the American Battle Monuments Commission (ABMC) by President George W. Bush in January 2005.",
        "John William Nicholson, Jr. (born May 8, 1957) is a United States Army general who most recently served as commanding general, Allied Land Command (since October 2014). Additionally he served as the commander of the 82nd Airborne Division."
        # Nicholson is the son of John W. Nicholson, also a former general officer in the United States Army. They are both distantly related to British Brigadier John Nicholson. On 4 February 2016, Nicholson was confirmed for a fourth star and to become General John F. Campbell's successor as commander of Resolute Support Mission and U.S. Forces Afghanistan (USFOR-A). He took over command from General Campbell on March 2, 2016."
    ]
    phrase = "In February, Gen. John Nicholson, commander of US forces in Afghanistan, told the Senate Armed Services Committee that leadership assesses \"the current security situation in Afghanistan as a stalemate.\""
    print(get_best_match(phrase, my_phrases))
    print(get_scores(phrase, my_phrases))