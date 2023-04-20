// See https://aka.ms/new-console-template for more information

using Splendor.Core.Model;
Card card = new Card("A", 1, new Dictionary<Color,int>(), Color.Black);

Console.WriteLine(card.String());

CoinSet cs = new CoinSet();
cs.Put(new KeyValuePair<Color, int>(Color.Black,10));
cs.Put(new KeyValuePair<Color, int>(Color.White,10));

Console.WriteLine(cs.String());